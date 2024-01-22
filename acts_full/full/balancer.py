from LoadBalancer import LOADBALANCER

#call the load balancing funciton from LoadBalance.py
with LOADBALANCER(image='acts',
							interval=120, 
							first_port=8000, 
							max_containers=10, 
							min_containers=1, 
							threshold=20, 
							health_check_time=1, 
							port = 80,
							volume_at = [7000,'/home/ubuntu/main/Acts/common','/common']
							) as loadbalancer:
	print("Deleting Remaining Containers")
	

