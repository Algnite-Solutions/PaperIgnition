import requests
import json
from typing import List, Dict

def batch_add_recommendations(recommendations: List[Dict]):
    """
    批量添加论文推荐记录
    
    Args:
        recommendations: 推荐记录列表，每个记录包含 username, paper_id, reason(可选), score(可选)
    """
    API_URL = "http://localhost:8000/api/papers/recommend"  # 根据实际后端地址修改
    
    success_count = 0
    fail_count = 0
    
    for rec in recommendations:
        try:
            response = requests.post(
                API_URL,
                json=rec,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 201:
                success_count += 1
                print(f"成功添加推荐: {rec['username']} - {rec['paper_id']}")
            else:
                fail_count += 1
                print(f"添加失败: {rec['username']} - {rec['paper_id']}")
                print(f"错误信息: {response.json()}")
                
        except Exception as e:
            fail_count += 1
            print(f"发生错误: {str(e)}")
    
    print(f"\n批量添加完成！成功: {success_count}, 失败: {fail_count}")

if __name__ == "__main__":
    # 示例数据
    recommendations = [
        {
            "username": "2273369951@qq.com",
            "paper_id": "2303.00001",
            "reason": "与用户研究兴趣相关",
            "relevance_score": 0.85
        },
        {
            "username": "2273369951@qq.com",
            "paper_id": "2303.00002",
            "reason": "最新研究进展",
            "relevance_score": 0.9
        }
    ]
    
    batch_add_recommendations(recommendations) 