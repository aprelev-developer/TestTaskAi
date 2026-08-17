import re, urllib.request, urllib.error, json
BASE="http://localhost:8080"

def get(path):
    req=urllib.request.Request(BASE+path, headers={"User-Agent":"qa-probe"})
    try:
        r=urllib.request.urlopen(req, timeout=10)
        return r.status, r.read().decode("utf-8","replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8","replace")
    except Exception as e:
        return -1, repr(e)

def cards(h):
    out=[]
    for c in re.findall(r'<div class="post-card">.*?(?=<div class="post-card">|</div>\s*</div>\s*$)', h, re.S):
        pid=re.search(r'/post/(\d+)',c)
        t=re.search(r'post-card__title">\s*<a[^>]*>(.*?)</a>',c,re.S)
        v=re.search(r'<span>(\d+) views?</span>',c)
        d=re.search(r'<time>(.*?)</time>',c)
        if pid: out.append((int(pid.group(1)), (t.group(1).strip() if t else None), (int(v.group(1)) if v else None), (d.group(1) if d else None)))
    return out

def text(h):
    b=re.search(r'<main.*?</main>|<body.*?</body>',h,re.S)
    return re.sub(r'\s+',' ',re.sub('<[^>]+>',' ',b.group(0))).strip() if b else ''

def title(h):
    m=re.search(r'<title>(.*?)</title>',h,re.S); return m.group(1).strip() if m else None

checks=[]
def rec(tid, url, note=""):
    st,h=get(url)
    checks.append(dict(id=tid,url=url,status=st,title=title(h),text=text(h)[:220],cards=cards(h),note=note))

rec("T01","/")
rec("T02","/category/programming")
rec("T03","/category/programming?sort=views")
rec("T04","/category/programming?sort=title")
rec("T05","/post/4")
rec("T06","/category/nonexistent")
rec("T07","/post/999999")
rec("T08","/post/abc")
rec("T09","/category/programming?page=2")
rec("T10a","/category/programming?page=0")
rec("T10b","/category/programming?page=-1")
rec("T10c","/category/programming?page=abc")
rec("T11","/category/programming?sort=hacked")
rec("EXTRA-sqli","/category/programming?sort=title'--")
rec("EXTRA-xss","/category/%3Cscript%3Ealert(1)%3C/script%3E")
rec("EXTRA-post0","/post/0")
rec("EXTRA-postneg","/post/-1")
rec("EXTRA-bigpage","/category/programming?page=99999999999999999999")

for c in checks:
    print("="*78)
    print(f"{c['id']}  {c['url']}  -> HTTP {c['status']}   <title>{c['title']}</title>")
    print("  карточек:", len(c['cards']))
    for pid,t,v,d in c['cards'][:10]:
        print(f"    id={pid:<4} views={v!s:<5} date={d!s:<20} {t}")
    print("  текст:", c['text'][:200])
