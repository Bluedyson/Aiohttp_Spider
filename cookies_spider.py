from IntervalTaskTimer import SimpleIntervalTaskTimer
import requests
import redis
import time
import random
import faker
fake = faker.Faker(locale='zh_CN')


class Douyin_cookies:
	def __init__(self, redis_pool: redis.ConnectionPool, cookies_db_name: str, ippool):
		self.redis_conn = redis.Redis(connection_pool=redis_pool)
		self.cookies_db_name = cookies_db_name
		self.request_timer = SimpleIntervalTaskTimer()
		self.delete_timer = SimpleIntervalTaskTimer()
		self.ippool = ippool

	def delete_cookies(self):
		# remove overtime cookies
		res = self.redis_conn.zremrangebyscore(self.cookies_db_name, 1, int(time.time() - 500))

		if res != 0:
			# if remove successful then print last num
			print("DELETE: {}".format(self.redis_conn.zcard(self.cookies_db_name)))

	def get_cookies(self):
		if len(self.redis_conn.zrange("cookies", 0, 1000)) != 0:
			return random.choice(self.redis_conn.zrange("cookies", 0, 1000)).decode("utf-8")
		else:
			print("NOT_COOKIES_USE: {}".format(self.redis_conn.zcard("cookies")))
			time.sleep(3)
			self.get_cookies()

	def request_data(self):
		print(("=" * 5) + "START_COOKIES" + ("=" * 5))
		try:
			res = requests.get(
				url="https://www.douyin.com/",
				headers={"User-Agent": fake.user_agent(), 'Connection': 'close', "Accept-Encoding": "gzip",
				         "referer": "https://www.douyin.com/",
				         "Content-Type": "application/json", "charset": "utf-8"},
				proxies=self.ippool.get_pool_ip(),
				timeout=30)
			print("res:{}".format(res.status_code))
			if res.status_code == 200 and res.text != "" and len(res.cookies.items()) != 0:
				cookies = ";".join([name + "=" + value for name, value in res.cookies.items()])
				print(cookies)
				self.redis_conn.zadd(self.cookies_db_name, {cookies: time.time()})
			else:
				raise ConnectionError

		except Exception as e:
			print("Failure: {} | {}".format(str(self.__class__), e))
			time.sleep(5)
			self.request_data()

	def run(self, deleteTime: int = 15, requestTime: int = 15):
		self.request_timer.run(requestTime, self.request_data())
		self.delete_timer.run(deleteTime, self.delete_cookies())
		print("Run: {}".format(str(self.__class__)), "=" * 50, self.request_timer.is_running(), self.delete_timer.is_running(), end="\n")
