from yami.main import entry

if __name__ == "__main__":
    try:
        entry()
    except Exception as e:
        print(f"程序运行出错: {e}")
