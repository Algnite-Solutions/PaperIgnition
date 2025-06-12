import requests
import json

def add_paper_recommendation(username: str, paper_id: str, reason: str = None, score: float = None):
    """
    添加论文推荐记录
    
    Args:
        username: 用户名
        paper_id: 论文ID
        reason: 推荐原因（可选）
        score: 相关性分数（可选，0-1之间）
    """
    # API地址
    API_URL = "http://localhost:8000/api/papers/recommend"  # 根据实际后端地址修改
    
    # 构建请求数据
    data = {
        "username": username,
        "paper_id": paper_id
    }
    
    # 添加可选字段
    if reason:
        data["recommendation_reason"] = reason
    if score is not None:
        data["relevance_score"] = score
    
    try:
        print("发送请求数据:", json.dumps(data, ensure_ascii=False, indent=2))
        
        # 发送POST请求
        response = requests.post(
            API_URL,
            json=data,
            headers={"Content-Type": "application/json"}
        )
        
        # 检查响应
        if response.status_code == 201:
            print("推荐记录添加成功！")
            print("响应数据:", response.json())
        else:
            print(f"添加失败，状态码: {response.status_code}")
            try:
                error_data = response.json()
                print("错误信息:", json.dumps(error_data, ensure_ascii=False, indent=2))
            except json.JSONDecodeError:
                print("原始响应内容:", response.text)
            
    except requests.exceptions.ConnectionError:
        print("连接错误：无法连接到服务器，请确保服务器正在运行")
    except requests.exceptions.RequestException as e:
        print(f"请求错误: {str(e)}")
    except Exception as e:
        print(f"发生未知错误: {str(e)}")

if __name__ == "__main__":
    # 示例调用
    add_paper_recommendation(
        username="2273369951@qq.com",  # 修正邮箱格式
        paper_id="2303.08770",
        reason="这篇论文与用户的研究兴趣高度相关",
        score=0.85
    ) 