# import time
# from groq import Groq   # assuming Groq provides a Python client
# import os
# from dotenv import load_dotenv

# load_dotenv()

# # Initialize Groq client
# client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# # def Korean2English(korean_text):
# #     start_time = time.time()
# #     response = client.chat.completions.create(
# #         model="moonshotai/kimi-k2-instruct",  # or "moonshotai/kimi-k2-0905"
# #         messages=[
# #             {"role": "system", "content": "You are a translation assistant that translates Korean to English."},
# #             {"role": "user", "content": korean_text}
# #         ]
# #     )
# #     english_text = response.choices[0].message.content
# #     elapsed = time.time() - start_time
# #     return english_text, elapsed

# def English2Korean(english_text):
#     start_time = time.time()
#     response = client.chat.completions.create(
#         model="moonshotai/kimi-k2-instruct",  # or "moonshotai/kimi-k2-0905"
#         messages=[
#             {"role": "system", "content": "You are a translation assistant that translates English to Korean."},
#             {"role": "user", "content": english_text}
#         ]
#     )
#     korean_text = response.choices[0].message.content
#     elapsed = time.time() - start_time
#     return korean_text, elapsed

# # Example usage

# kor, t1 = English2Korean("I am fine, thank you. How about you? Where are you from? And why do you want to learn Korean? I can help you with that. Also If you have any questions about Korean culture or history, feel free to ask me.")
# print(kor, f"(took {t1:.2f} s)")

# # eng, t2 = Korean2English(kor)
# # print(eng, f"(took {t2:.2f} s)")


from murf import Murf
import os
from dotenv import load_dotenv
load_dotenv()
client = Murf(api_key=os.getenv("MURF_API_KEY"), timeout=300)

response = client.text_to_speech.generate(
    text="""
    저는 지금까지의 여정을 돌아보면, 단순히 기술적 성과만으로 성장해온 것이 아니라 사람들과의 만남과 경험이 저를 크게 변화시켰다고 느낍니다. 함께 공부하고, 토론하고, 협력하는 과정에서 저는 항상 새로운 관점을 얻었고, 그것이 저를 더 넓은 세상으로 이끌었습니다. 저는 앞으로도 이런 만남과 협력을 통해 배움을 이어가고 싶습니다. 기술은 혼자서 완성할 수 없는 것이며, 사람들과의 관계 속에서 비로소 그 가치를 발휘한다고 생각하기 때문입니다. 저는 언젠가 연구자와 개발자로서, 그리고 교육자로서도 다른 사람들에게 영감을 줄 수 있는 위치에 서고 싶습니다. 단순히 제가 배운 지식을 전달하는 것이 아니라, 다른 사람들이 자신의 잠재력을 발견하고 성장할 수 있도록 돕는 역할을 하고 싶습니다. 또한 기술을 통해 사회 문제를 해결하는 동시에, 사람들의 삶을 더 따뜻하고 의미 있게 만들고 싶습니다. 결국 제가 추구하는 길은 개인적인 성취에 머무르지 않고, 사회 전체와 함께 성장하며 긍정적인 영향을 남기는 것입니다. 그래서 오늘도 저는 작은 도전이라도 기꺼이 받아들이고, 실패를 두려워하지 않으며, 더 나은 내일을 향해 꾸준히 나아가고 있습니다.
    """,
    voice_id="ko-KR-jangmi",
    style="Conversational",
    pitch=1,
    rate=-13
)

print(response.audio_file)
