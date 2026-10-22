#!/usr/bin/env python3
"""Back up the planner's data to Amazon S3. No dependencies.

Packs data.json, users.json, profiles/ and images/ into one .tar.gz and uploads it
as <prefix>/YYYY/MM/meal-planner-YYYYMMDD-HHMMSS.tar.gz, but only when something
changed since the last upload. Run it from cron every 15 minutes or so.

Settings (environment, or KEY=value lines in a .env next to this file):
  S3_BUCKET              bucket name (required)
  S3_REGION              e.g. eu-central-1 (required)
  AWS_ACCESS_KEY_ID      key that may only s3:PutObject (required)
  AWS_SECRET_ACCESS_KEY  (required)
  S3_PREFIX              folder in the bucket, default "meal-planner"
  S3_ENDPOINT            only for S3-compatible services or testing, e.g. http://127.0.0.1:9000

  python3 backup_s3.py           upload if the data changed
  python3 backup_s3.py --force   upload even if nothing changed
"""
import datetime, hashlib, hmac, io, json, os, sys, tarfile, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
FILES = ["data.json", "users.json"]
DIRS = ["profiles", "images"]
STAMP = os.path.join(HERE, ".backup-s3-last")


def load_dotenv(path):
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k, v = k.strip().removeprefix("export "), v.strip().strip('"').strip("'")
                if k and k not in os.environ:
                    os.environ[k] = v
    except FileNotFoundError:
        pass


def fingerprint():
    """Hash of every backed-up file's name, size and contents, so unchanged data isn't re-uploaded."""
    h = hashlib.sha256()
    paths = [p for p in FILES if os.path.isfile(os.path.join(HERE, p))]
    for d in DIRS:
        for root, _, names in os.walk(os.path.join(HERE, d)):
            paths += [os.path.relpath(os.path.join(root, n), HERE) for n in names]
    for p in sorted(paths):
        h.update(p.encode() + b"\0")
        with open(os.path.join(HERE, p), "rb") as f:
            h.update(hashlib.sha256(f.read()).digest())
    return h.hexdigest(), sorted(paths)


def pack(paths):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for p in paths:
            tar.add(os.path.join(HERE, p), arcname=p)
    return buf.getvalue()


def sign(method, host, path, region, headers, payload_hash, key_id, secret, now):
    """AWS Signature Version 4 for a request with no query string. Returns the Authorization header."""
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    day = amz_date[:8]
    canon_headers = "".join(f"{k}:{headers[k].strip()}\n" for k in sorted(headers))
    signed = ";".join(sorted(headers))
    canon = "\n".join([method, urllib.parse.quote(path, safe="/~"), "", canon_headers, signed, payload_hash])
    scope = f"{day}/{region}/s3/aws4_request"
    to_sign = "\n".join(["AWS4-HMAC-SHA256", amz_date, scope, hashlib.sha256(canon.encode()).hexdigest()])
    k = ("AWS4" + secret).encode()
    for part in (day, region, "s3", "aws4_request"):
        k = hmac.new(k, part.encode(), hashlib.sha256).digest()
    sig = hmac.new(k, to_sign.encode(), hashlib.sha256).hexdigest()
    return f"AWS4-HMAC-SHA256 Credential={key_id}/{scope}, SignedHeaders={signed}, Signature={sig}"


def upload(body, key):
    bucket, region = os.environ["S3_BUCKET"], os.environ["S3_REGION"]
    key_id, secret = os.environ["AWS_ACCESS_KEY_ID"], os.environ["AWS_SECRET_ACCESS_KEY"]
    endpoint = os.environ.get("S3_ENDPOINT", "").rstrip("/")
    if endpoint:  # path-style: http://host:port/bucket/key
        u = urllib.parse.urlparse(endpoint)
        scheme, host, path = u.scheme, u.netloc, f"/{bucket}/{key}"
    else:
        scheme, host, path = "https", f"{bucket}.s3.{region}.amazonaws.com", f"/{key}"
    now = datetime.datetime.now(datetime.timezone.utc)
    payload_hash = hashlib.sha256(body).hexdigest()
    headers = {"host": host, "x-amz-content-sha256": payload_hash,
               "x-amz-date": now.strftime("%Y%m%dT%H%M%SZ"), "content-type": "application/gzip"}
    auth = sign("PUT", host, path, region, headers, payload_hash, key_id, secret, now)
    req = urllib.request.Request(f"{scheme}://{host}{urllib.parse.quote(path, safe='/~')}", data=body, method="PUT",
                                 headers={**{k: v for k, v in headers.items() if k != "host"}, "Authorization": auth})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.status


def main():
    load_dotenv(os.path.join(HERE, ".env"))
    missing = [k for k in ("S3_BUCKET", "S3_REGION", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY") if not os.environ.get(k)]
    now = datetime.datetime.now(datetime.timezone.utc)
    log = lambda msg: print(now.strftime("%Y-%m-%d %H:%M:%S"), msg)
    if missing:
        log("not set: " + ", ".join(missing)); return 1
    fp, paths = fingerprint()
    if not paths:
        log("nothing to back up"); return 1
    try:
        last = open(STAMP).read().strip()
    except FileNotFoundError:
        last = ""
    if fp == last and "--force" not in sys.argv:
        return 0
    body = pack(paths)
    prefix = os.environ.get("S3_PREFIX", "meal-planner").strip("/")
    key = f"{prefix}/{now:%Y/%m}/meal-planner-{now:%Y%m%d-%H%M%S}.tar.gz"
    try:
        upload(body, key)
    except urllib.error.HTTPError as e:
        log(f"upload failed: HTTP {e.code} {e.read()[:300].decode('utf-8', 'replace')}"); return 1
    except Exception as e:
        log(f"upload failed: {e}"); return 1
    with open(STAMP, "w") as f:
        f.write(fp)
    log(f"uploaded {key} ({len(body) // 1024} KB, {len(paths)} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
