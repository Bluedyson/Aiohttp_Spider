import requests
import json
import redis
import time
from IntervalTaskTimer import SimpleIntervalTaskTimer
import random


class Ip_pool:
	def __init__(self,
	             redis_pool: redis.ConnectionPool,
	             ippool_db_name: str,
	             api_url: str,
	             api_username: str,
	             api_password: str):
		self.redis_conn = redis.Redis(connection_pool=redis_pool)
		self.ippool_db_name = ippool_db_name
		self.request_timer = SimpleIntervalTaskTimer()
		self.delete_timer = SimpleIntervalTaskTimer()
		self.api_url = api_url
		self.api_username = api_username
		self.api_password = api_password

	def delete_ip(self):
		self.redis_conn.zremrangebyscore(self.ippool_db_name, 1, int(time.time()))

	def get_pool_ip(self):
		if len(self.redis_conn.zrangebyscore(self.ippool_db_name, int(time.time()), 9999999999)) != 0:
			return json.loads(
				random.choice(self.redis_conn.zrangebyscore(self.ippool_db_name, int(time.time()), 9999999999)).decode("utf-8")
			)
		else:
			print("NOT_IP_USE: {} | {}".format(
				self.redis_conn.zcard(self.ippool_db_name),
				str(self.__class__)
			))
			time.sleep(3)
			self.get_pool_ip()

	def get_ip(self):
		rawdata = {}
		# 获取API接口返回的代理IP
		try:
			rawdata = json.loads(requests.get(self.api_url).text)
		except Exception as e:
			print("Failure: {} | {}".format(e, str(self.__class__)))
			yield {}

		for i in range(len(rawdata["data"]["proxy_list"])):
			proxy_ip = rawdata["data"]["proxy_list"][i]
			# 用户名密码认证(动态代理/独享代理)
			proxies = {
				"http": "http://%(user)s:%(pwd)s@%(proxy)s/" % {"user": self.api_username, "pwd": self.api_password,
				                                                "proxy": proxy_ip.split(",")[0]},
				"https": "http://%(user)s:%(pwd)s@%(proxy)s/" % {"user": self.api_username, "pwd": self.api_password,
				                                                 "proxy": proxy_ip.split(",")[0]}
			}
			yield {"proxies": proxies, "canUseTime": proxy_ip.split(",")[1]}

	def dynamic_addIP(self):
		for i in self.get_ip():
			if len(i) != 0:
				self.redis_conn.zadd(self.ippool_db_name, {json.dumps(i["proxies"]): int(time.time() + eval(i["canUseTime"]))})

	def run(self):
		self.request_timer.run(3, self.dynamic_addIP)
		self.delete_timer.run(1, self.delete_ip)
		print("Run: {}".format(str(self.__class__)), "=" * 50, self.request_timer.is_running(), self.delete_timer.is_running(), end="\n")
