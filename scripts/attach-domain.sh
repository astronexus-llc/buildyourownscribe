#!/usr/bin/env bash
# One-time: attach scribe.health201.com to the Cloudflare Pages project
# "buildyourscribe" and create its proxied CNAME on the health201.com zone.
# Uses AN201_CLOUDFLARE_API_TOKEN from the vault (/run/secrets/master.env), so
# run it on the workstation. Safe to re-run: it reports what already exists.
set -uo pipefail
TOKEN="$(grep -m1 '^AN201_CLOUDFLARE_API_TOKEN=' /run/secrets/master.env 2>/dev/null | cut -d= -f2-)"
[ -n "$TOKEN" ] || { echo "no token (is /run/secrets/master.env mounted?)"; exit 1; }
PROJECT=buildyourscribe
ZONE_NAME=health201.com
HOST=scribe.health201.com
TARGET=buildyourscribe.pages.dev
API=https://api.cloudflare.com/client/v4
H=(-H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json")
cf(){ curl -s --max-time 20 "${H[@]}" "$@"; }
ok(){ python3 -c 'import json,sys;d=json.load(sys.stdin);print("success" if d.get("success") else d.get("errors"))'; }

ZONE_JSON=$(cf "$API/zones?name=$ZONE_NAME")
ZONE=$(echo "$ZONE_JSON" | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d["result"][0]["id"] if d.get("result") else "")')
ACCT=$(echo "$ZONE_JSON" | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d["result"][0]["account"]["id"] if d.get("result") else "")')
echo "zone: ${ZONE:+found}${ZONE:-NOT FOUND}"
[ -n "$ZONE" ] || exit 1

echo "--- pages domain"
cf -X POST "$API/accounts/$ACCT/pages/projects/$PROJECT/domains" -d "{\"name\":\"$HOST\"}" | ok

echo "--- dns record"
EXIST=$(cf "$API/zones/$ZONE/dns_records?name=$HOST" | python3 -c 'import json,sys;d=json.load(sys.stdin);print(len(d.get("result",[])))')
if [ "$EXIST" = "0" ]; then
  cf -X POST "$API/zones/$ZONE/dns_records" -d "{\"type\":\"CNAME\",\"name\":\"scribe\",\"content\":\"$TARGET\",\"proxied\":true,\"ttl\":1}" | ok
else
  echo "already exists ($EXIST record)"
fi

echo "--- status (can take a minute or two)"
for _ in $(seq 1 12); do
  S=$(cf "$API/accounts/$ACCT/pages/projects/$PROJECT/domains/$HOST" | python3 -c 'import json,sys;d=json.load(sys.stdin);r=d.get("result") or {};print(r.get("status"),r.get("validation_data",{}).get("status"))')
  echo "$S"; case "$S" in active*) break;; esac; sleep 10
done
