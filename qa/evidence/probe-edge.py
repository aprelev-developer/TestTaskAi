import re, urllib.request, urllib.error
BASE="http://localhost:8080"
def get(path, method="GET"):
    req=urllib.request.Request(BASE+path, headers={"User-Agent":"qa-probe"}, method=method)
    try:
        r=urllib.request.urlopen(req, timeout=10)
        return r.status, dict(r.headers), r.read().decode("utf-8","replace")
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode("utf-8","replace")
    except Exception as e:
        return -1, {}, repr(e)
def ids(h): 
    seen=[];  
    for m in re.findall(r'post-card__title">\s*<a href="/post/(\d+)"',h): 
        seen.append(int(m))
    return seen
def msg(h):
    b=re.search(r'<main.*?</main>|<body.*?</body>',h,re.S)
    return re.sub(r'\s+',' ',re.sub('<[^>]+>',' ',b.group(0))).strip()[:150] if b else ''

for p in ["/category/programming","/category/programming?sort=views","/category/programming?sort=title",
          "/category/programming/","/category/Programming","/category/PROGRAMMING",
          "/category/programming?page=1","/category/programming?page=01","/category/programming?page=1.5",
          "/category/programming?page=%20","/category/programming?page=","/category/programming?sort=",
          "/category/programming?sort=date&page=abc","/post/04","/post/4.0","/post/+4"]:
    st,hd,h=get(p)
    print(f"{p:<48} {st}  ids={ids(h)}  | {msg(h)[:70]}")
print("--- методы ---")
for m in ["POST","PUT","DELETE","HEAD"]:
    st,hd,h=get("/",method=m); print(f"{m:<7} / -> {st}  {msg(h)[:80]}")
print("--- заголовки главной ---")
st,hd,h=get("/")
for k,v in hd.items(): print(f"  {k}: {v}")
