# Quick-Start
## Clone the source code
```text
git clone ()
cd Aiohttp_spider
```

## prepared work

- If you want to use your  Ip_source you should:
   - I use xx source.
     - Change the `ip_pool_spider.py` and replaced by your id.
   - I use other source
     - Change the `get_ip` in `Ip_pool_spider`
     - The `get_ip` after modify, it should yield a dict.  
     ```
        {
            "proxies":{"http": Address, "https": Address}, 
            "canUseTime": int_remainder_unit:second
        }
     ```
- Config the source of redis, which in `Main_comments_spider.py`.
  - Create the Database in redis, and keep the same name both redis and `Main_comments_spider.py`
- Config your grab aim, which located in `judge()` in `Main_comments_spider.py`.
- Config your download folder in `Main_comments_spider.py`.
## Start
```
python Main_comments_spider.py
```

# Architecture

```text
├─Spider
│  ├─Mian_comments_spider.py 
│  ├─Ip_pool_spider.py
│  ├─Cookies_spider.py
```
