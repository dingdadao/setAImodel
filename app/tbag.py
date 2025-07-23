import hashlib


def calc_md5(ip, ua, referer, url):
    s = ip + ua + referer + url
    return hashlib.md5(s.encode('utf-8')).hexdigest()