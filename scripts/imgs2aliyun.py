import oss2
import os
import time

# 配置
access_key_id = '
access_key_secret = '
endpoint = 'https://oss-cn-beijing.aliyuncs.com'
bucket_name = 'paperignition'

# 创建Bucket对象，设置更长的超时时间
auth = oss2.Auth(access_key_id, access_key_secret)
bucket = oss2.Bucket(auth, endpoint, bucket_name, connect_timeout=60)

# 本地图片文件夹
local_folder = '/data3/guofang/peirongcan/PaperIgnition/orchestrator/imgs'

# 获取OSS上已存在的文件列表
existing_files = set()
for obj in oss2.ObjectIterator(bucket, prefix='imgs/'):
    existing_files.add(obj.key)
print(f'OSS上已有 {len(existing_files)} 个文件')

# 上传函数，带重试
def upload_with_retry(oss_path, local_path, max_retries=3):
    for attempt in range(max_retries):
        try:
            bucket.put_object_from_file(oss_path, local_path)
            return True
        except Exception as e:
            print(f'  重试 {attempt + 1}/{max_retries}: {e}')
            time.sleep(2)
    return False

# 上传所有文件
failed_files = []
for filename in os.listdir(local_folder):
    local_path = os.path.join(local_folder, filename)
    if os.path.isfile(local_path):
        oss_path = f'imgs/{filename}'
        
        # 跳过已上传的文件
        if oss_path in existing_files:
            # print(f'跳过(已存在): {filename}')
            continue
        
        print(f'上传中: {filename}...', end=' ')
        if upload_with_retry(oss_path, local_path):
            print('成功')
        else:
            print('失败')
            failed_files.append(filename)

print(f'\n上传完成！失败文件数: {len(failed_files)}')
if failed_files:
    print('失败文件列表:')
    for f in failed_files:
        print(f'  - {f}')