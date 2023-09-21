"""
coding:utf-8
@Time:2022/12/10 0:45
"""
import json
import faker
import aiohttp
import asyncio
import redis
import os
from ip_pool_spider import Ip_pool
from cookies_spider import Douyin_cookies

"""
ip and cookies from lists

control =>producer
save => event driven
getter => consumer

separate maintainer and getter
"""

fake = faker.Faker(locale='zh_CN')
redis_pool = redis.ConnectionPool(host='127.0.0.1', port=6379, db=0)
redis_conn = redis.Redis(connection_pool=redis_pool)
ip_pool = Ip_pool(redis_pool, "new_ippool", "ip_pool_source_url", api_username="username", api_password="password")
cookies = Douyin_cookies(redis_pool, "new_cookies", ip_pool)


class Args:
	video_list = []
	save_path = "./down_new"
	video_progress = "video_pool_new"


class spider:
	def __init__(self, video_list: [], args: Args):
		self.args = args

		# TODO: session control
		self.session = aiohttp.ClientSession(
			headers={"User-Agent": fake.user_agent(), "Accept-Encoding": "gzip",
			         "referer": "https://www.douyin.com/",
			         "Content-Type": "application/json", "charset": "utf-8"},
			timeout=5)

		self.video_list = video_list
		self.request_queue = asyncio.Queue()
		self.save_queue = asyncio.Queue()
		self.thread = {
			"request": 10,
			"save": 3,
		}

		# check existence of path and progress of each video
		for video_id in self.video_list:
			if not os.path.exists(r"./down_new/{}".format(video_id)):
				os.mkdir(r"./down_new/{}".format(video_id))

			if redis_conn.zscore(self.args.video_progress, video_id) is None:
				redis_conn.zadd(self.args.video_progress, {video_id: 0})

	async def main(self):
		# create grab task
		for video_id in self.video_list:
			await self.request_queue.put({
				"comment": "",
				"get_count": 0,
				"cursor": max(int(redis_conn.zscore(self.args.video_progress, video_id)), 0),
				"video_id": video_id
			})

		# create new co-thread
		tasks = []
		for i in range(self.thread["request"]):
			tasks.append(asyncio.create_task(self.request()))

		for i in range(self.thread["save"]):
			tasks.append(asyncio.create_task(self.save_to_file()))

		await asyncio.gather(*tasks)
		await self.request_queue.join()
		await self.save_queue.join()

	async def judge(self, task):
		if task["comment"] == "" and task["get_count"] > 2:
			print("Complete:{}  {}".format(task["video_id"], task["cursor"]))
		elif task["get_count"] <= 2:
			await self.request_queue.put(task)
		else:
			task["comment"] = json.loads(task["comment"])

			if task["comment"].get("comments") is None:
				await self.request_queue.put(task)
			else:
				comments = []
				for com in task["comment"].get("comments"):
					comments.append(com)

				task["get_count"] = 0
				task["cursor"] += 50
				task["comment"] = []

				await self.request_queue.put(task)
				await self.save_queue.put(task)
				await redis_conn.zadd(self.args.video_progress, {task["video_id"]: task["cursor"]})
				print('Success: {}_{}'.format(task["video_id"], task["cursor"]))

	async def request(self):
		# get a grab task for queue, and send request
		while True:
			task = await self.request_queue.get()
			try:
				async with self.session.get(
						url="https://www.douyin.com/aweme/v1/web/comment/list/?device_platform=webapp&aid=6383&channel=channel_pc_web&aweme_id={}&cursor={}&count=50"
								.format(task["video_id"], task["cursor"]),
						cookies=cookies.get_cookies(),
						proxy=ip_pool.get_pool_ip()) as response:
					task["get_count"] += 1
					assert response.status == 200
					task["comment"] = await response.read()
					await self.judge(task)
					self.request_queue.task_done()

			except Exception as e:
				if task["get_count"] <= 5:
					await self.request_queue.put(task)
					print("ERROR: {}_{}".format(task["video_id"], task["cursor"]))
				else:
					print("Complete[Error]:{}_{}".format(task["video_id"], task["cursor"]))
				self.request_queue.task_done()

	async def save_to_file(self):
		while True:
			result = await self.save_queue.get()
			with open(self.args.save_path + "/{0}/{0}_{1}.txt".format(result["video_id"], result["cursor"]), "w") as f:
				f.write(json.dumps(result["comments"]))
			self.save_queue.task_done()
