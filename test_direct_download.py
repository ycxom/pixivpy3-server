"""
测试直接从 Pixiv CDN 下载图片（客户端添加 Referer 头）
"""
import requests
import os

# Pixiv 图片 URL（从排行榜获取的示例）
IMAGE_URL = "https://i.pximg.net/c/600x1200_90_webp/img-master/img/2025/10/04/13/31/40/135858440_p0_master1200.jpg"

# Pixiv 需要的请求头
HEADERS = {
    "Referer": "https://www.pixiv.net/",
    "User-Agent": "PixivIOSApp/7.13.3 (iOS 14.6; iPhone13,2)"
}

# 代理设置（从 config.yaml 读取或手动设置）
PROXIES = {
    "http": "http://127.0.0.1:10808",
    "https": "http://127.0.0.1:10808"
}

def test_direct_download(use_proxy=True):
    """测试直接下载"""
    filename = os.path.basename(IMAGE_URL)
    output_path = f"./{filename}"
    
    print(f"Downloading: {IMAGE_URL}")
    print(f"Headers: {HEADERS}")
    print(f"Proxy: {PROXIES if use_proxy else 'None'}")
    print(f"Output: {output_path}")
    
    try:
        proxies = PROXIES if use_proxy else None
        response = requests.get(IMAGE_URL, headers=HEADERS, proxies=proxies, timeout=60)
        
        if response.status_code == 200:
            with open(output_path, 'wb') as f:
                f.write(response.content)
             
            file_size = os.path.getsize(output_path)
            print(f"\n✓ Download success!")
            print(f"  File: {output_path}")
            print(f"  Size: {file_size} bytes")
            return True
        else:
            print(f"\n✗ Download failed!")
            print(f"  Status: {response.status_code}")
            print(f"  Response: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False

if __name__ == "__main__":
    test_direct_download(use_proxy=True)
