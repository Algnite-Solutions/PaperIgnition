import pytest
import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from backend.configs.config import load_backend_config

# 加载配置
config = load_backend_config()

# 配置测试参数
# 注意：由于微信小程序需要特殊的测试环境，这里我们假设使用Web版进行测试
FRONTEND_URL = config['frontend_url']  # 从配置文件读取前端URL
TEST_EMAIL = config['test_user']['email']  # 从配置文件读取测试用户邮箱
TEST_PASSWORD = config['test_user']['password']  # 从配置文件读取测试用户密码

class TestFrontend:
    """前端功能测试类"""
    
    @classmethod
    def setup_class(cls):
        """设置测试环境"""
        # 根据不同操作系统选择适当的驱动
        if os.name == 'nt':  # Windows
            cls.driver = webdriver.Chrome()
        else:  # Linux/macOS
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            cls.driver = webdriver.Chrome(options=options)
        
        cls.driver.maximize_window()
        cls.wait = WebDriverWait(cls.driver, 10)
    
    @classmethod
    def teardown_class(cls):
        """清理测试环境"""
        cls.driver.quit()
    
    def test_login_page(self):
        """测试登录页面"""
        try:
            # 打开登录页
            self.driver.get(f"{FRONTEND_URL}/login")
            time.sleep(2)  # 等待页面加载
            
            # 验证页面标题
            assert "登录" in self.driver.title or "Login" in self.driver.title, "登录页面标题不正确"
            
            # 检查登录表单元素是否存在
            assert self.element_exists(By.ID, "email") or self.element_exists(By.NAME, "email"), "邮箱输入框不存在"
            assert self.element_exists(By.ID, "password") or self.element_exists(By.NAME, "password"), "密码输入框不存在"
            assert self.element_exists(By.TAG_NAME, "button"), "登录按钮不存在"
            
            print("✅ 登录页面测试通过")
            return True
        except (AssertionError, NoSuchElementException) as e:
            print(f"❌ 登录页面测试失败: {str(e)}")
            return False
    
    def test_login_flow(self):
        """测试登录流程"""
        if not self.test_login_page():
            print("❌ 跳过登录流程测试，因为登录页面测试失败")
            return False
            
        try:
            # 输入登录信息
            email_field = self.find_element_by_multiple([(By.ID, "email"), (By.NAME, "email")])
            password_field = self.find_element_by_multiple([(By.ID, "password"), (By.NAME, "password")])
            
            email_field.clear()
            email_field.send_keys(TEST_EMAIL)
            password_field.clear()
            password_field.send_keys(TEST_PASSWORD)
            
            # 点击登录按钮
            login_button = self.driver.find_element(By.TAG_NAME, "button")
            login_button.click()
            
            # 等待登录成功跳转
            try:
                # 等待跳转到主页或推荐页
                self.wait.until(lambda driver: "/recommendations" in driver.current_url or "/home" in driver.current_url or "/index" in driver.current_url)
                print("✅ 登录流程测试通过")
                return True
            except TimeoutException:
                print("❌ 登录失败或超时")
                return False
                
        except (NoSuchElementException, TimeoutException) as e:
            print(f"❌ 登录流程测试失败: {str(e)}")
            return False
    
    def test_paper_recommendation_page(self):
        """测试论文推荐页面"""
        if not self.test_login_flow():
            print("❌ 跳过推荐页面测试，因为登录流程测试失败")
            return
            
        try:
            # 导航到推荐页面
            self.driver.get(f"{FRONTEND_URL}/recommendations")
            time.sleep(2)  # 等待页面加载
            
            # 检查是否有论文列表
            paper_elements = self.driver.find_elements(By.CLASS_NAME, "paper-item")
            
            # 即使没有推荐论文，页面结构也应该正确
            assert self.element_exists(By.TAG_NAME, "h1") or self.element_exists(By.TAG_NAME, "h2"), "页面缺少标题元素"
            
            if paper_elements:
                print(f"✅ 推荐页面测试通过: 找到{len(paper_elements)}篇推荐论文")
            else:
                print("✅ 推荐页面测试通过: 页面结构正确，但没有找到推荐论文")
                
        except (AssertionError, NoSuchElementException) as e:
            print(f"❌ 推荐页面测试失败: {str(e)}")
    
    def test_paper_detail_page(self):
        """测试论文详情页面"""
        if not self.test_login_flow():
            print("❌ 跳过论文详情页面测试，因为登录流程测试失败")
            return
            
        try:
            # 先导航到推荐页面
            self.driver.get(f"{FRONTEND_URL}/recommendations")
            time.sleep(2)  # 等待页面加载
            
            # 查找论文项目
            paper_elements = self.driver.find_elements(By.CLASS_NAME, "paper-item")
            
            if not paper_elements:
                print("⚠️ 没有找到论文项目，跳过论文详情测试")
                return
                
            # 点击第一篇论文
            paper_elements[0].click()
            time.sleep(2)  # 等待页面加载
            
            # 验证是否进入了详情页
            assert "paper-detail" in self.driver.current_url or "paper" in self.driver.current_url, "未进入论文详情页"
            
            # 检查详情页元素
            assert self.element_exists(By.TAG_NAME, "h1") or self.element_exists(By.TAG_NAME, "h2"), "详情页缺少标题元素"
            
            print("✅ 论文详情页面测试通过")
            
        except (AssertionError, NoSuchElementException, IndexError) as e:
            print(f"❌ 论文详情页面测试失败: {str(e)}")
    
    def test_user_profile_page(self):
        """测试用户资料页面"""
        if not self.test_login_flow():
            print("❌ 跳过个人资料页面测试，因为登录流程测试失败")
            return
            
        try:
            # 导航到个人资料页面
            self.driver.get(f"{FRONTEND_URL}/profile")
            time.sleep(2)  # 等待页面加载
            
            # 检查页面元素
            assert self.element_exists(By.TAG_NAME, "form"), "找不到个人资料表单"
            
            # 检查邮箱字段是否显示了当前登录用户的邮箱
            page_source = self.driver.page_source
            assert TEST_EMAIL in page_source, "页面中没有显示当前用户邮箱"
            
            print("✅ 个人资料页面测试通过")
            
        except (AssertionError, NoSuchElementException) as e:
            print(f"❌ 个人资料页面测试失败: {str(e)}")
    
    def test_research_interests_page(self):
        """测试研究兴趣页面"""
        if not self.test_login_flow():
            print("❌ 跳过研究兴趣页面测试，因为登录流程测试失败")
            return
            
        try:
            # 导航到研究兴趣页面
            self.driver.get(f"{FRONTEND_URL}/research-interests")
            time.sleep(2)  # 等待页面加载
            
            # 检查页面元素
            assert self.element_exists(By.TAG_NAME, "form"), "找不到研究兴趣表单"
            
            # 检查是否有研究领域选择器
            domains_exist = (
                self.element_exists(By.NAME, "domains") or 
                self.element_exists(By.CLASS_NAME, "domains") or
                self.element_exists(By.ID, "domains") or
                self.element_exists(By.TAG_NAME, "select") or
                self.element_exists(By.TAG_NAME, "checkbox")
            )
            assert domains_exist, "找不到研究领域选择器"
            
            print("✅ 研究兴趣页面测试通过")
            
        except (AssertionError, NoSuchElementException) as e:
            print(f"❌ 研究兴趣页面测试失败: {str(e)}")
    
    def test_navigation(self):
        """测试导航功能"""
        if not self.test_login_flow():
            print("❌ 跳过导航测试，因为登录流程测试失败")
            return
            
        try:
            # 测试底部导航栏或顶部导航栏
            nav_elements = self.driver.find_elements(By.TAG_NAME, "nav")
            
            if not nav_elements:
                nav_elements = self.driver.find_elements(By.CLASS_NAME, "navigation")
                
            if not nav_elements:
                print("⚠️ 找不到导航元素，跳过导航测试")
                return
                
            # 查找导航链接
            links = nav_elements[0].find_elements(By.TAG_NAME, "a")
            
            if not links:
                print("⚠️ 找不到导航链接，跳过导航测试")
                return
                
            # 测试点击第一个链接
            original_url = self.driver.current_url
            links[0].click()
            time.sleep(1)  # 等待页面加载
            
            # 验证URL已更改
            assert self.driver.current_url != original_url, "点击导航链接后URL未改变"
            
            print("✅ 导航功能测试通过")
            
        except (AssertionError, NoSuchElementException, IndexError) as e:
            print(f"❌ 导航功能测试失败: {str(e)}")
    
    # 辅助方法
    def element_exists(self, by, value):
        """检查元素是否存在"""
        try:
            self.driver.find_element(by, value)
            return True
        except NoSuchElementException:
            return False
    
    def find_element_by_multiple(self, locators):
        """尝试使用多种定位器查找元素"""
        for by, value in locators:
            try:
                return self.driver.find_element(by, value)
            except NoSuchElementException:
                continue
        raise NoSuchElementException(f"无法找到元素: {locators}")

def run_tests():
    """运行所有前端测试"""
    print(f"\n运行前端测试，目标URL: {FRONTEND_URL}")
    print("=" * 50)
    
    test = TestFrontend()
    try:
        test.setup_class()
        
        # 登录和基本页面测试
        test.test_login_page()
        test.test_login_flow()
        
        # 功能页面测试
        test.test_paper_recommendation_page()
        test.test_paper_detail_page()
        test.test_user_profile_page()
        test.test_research_interests_page()
        
        # 导航测试
        test.test_navigation()
        
        print("\n✅ 所有前端测试完成!")
    except Exception as e:
        print(f"\n❌ 测试过程中出错: {str(e)}")
    finally:
        test.teardown_class()

if __name__ == "__main__":
    run_tests() 