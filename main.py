def main():
    print("Hello from b2-1!")

    import requests

    response = requests.post(
        "https://copa.codyssey.kr/v1/chat/completions",
        headers={
            "Authorization": "Bearer sk-cody-live-hJ2iHG_vX0jiSfErKIWEs_rQ-_2SJvPivsPkyz1dCsk"
        },
        json={
            "model": "gpt-5-mini",
            "messages": [{"role": "user", "content": "안녕하세요"}],
        },
    )
    print(response.json())


if __name__ == "__main__":
    main()
