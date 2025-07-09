from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp
import whisper
import openai
import os
import tempfile
import json
from typing import Optional

app = FastAPI(title="Yorist Backend API", version="1.0.0")

# CORS 설정 (프론트엔드에서 접근 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 환경 변수에서 API 키 로드
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

@app.get("/")
async def root():
    """헬스 체크 엔드포인트"""
    return {"message": "Yorist Backend API is running!"}

@app.get("/generate-recipe")
async def generate_recipe_from_shorts(youtube_url: str = Query(..., description="유튜브 쇼츠 URL")):
    """
    유튜브 쇼츠에서 레시피를 자동 생성하는 엔드포인트
    
    처리 과정:
    1. yt-dlp로 오디오 다운로드
    2. Whisper로 음성→텍스트 변환
    3. OpenAI GPT로 레시피 JSON 생성
    """
    try:
        print(f"[generate-recipe] 시작: {youtube_url}")
        
        # OpenAI API 키 확인
        if not OPENAI_API_KEY:
            raise HTTPException(status_code=500, detail="OpenAI API 키가 설정되지 않았습니다.")
        
        # 임시 디렉토리 생성
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = os.path.join(temp_dir, "audio.mp3")
            
            print(f"[generate-recipe] 1단계: 오디오 다운로드 시작")
            
            # 1. yt-dlp로 오디오 다운로드
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': audio_path.replace('.mp3', ''),
                'quiet': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([youtube_url])
            
            print(f"[generate-recipe] 2단계: Whisper 모델 로드")
            
            # 2. Whisper로 자막 추출
            model = whisper.load_model("base")  # 또는 "small", "medium"
            
            print(f"[generate-recipe] 3단계: 음성→텍스트 변환")
            result = model.transcribe(audio_path)
            transcript = result["text"]
            
            print(f"[generate-recipe] 자막 추출 완료 (길이: {len(transcript)}자)")
            
            # 3. OpenAI GPT로 레시피 JSON 생성
            print(f"[generate-recipe] 4단계: GPT 레시피 생성")
            
            openai.api_key = OPENAI_API_KEY
            
            # 레시피 생성 프롬프트
            prompt = f"""아래 유튜브 영상의 자막을 분석해서, 요리 레시피 데이터를 JSON 형식으로 만들어줘.

자막이 긴 경우라도, 요리 흐름과 순서를 고려해 최대 10단계 이내로 조리 단계를 정리해줘.
각 조리 단계는 문장이 너무 길지 않도록 간결하게 작성하되, **중요한 조리 절차는 절대 생략하지 말 것**.
추출된 재료들은 **모두 조리 단계 안에서 실제로 사용되도록** 단계 내 설명에 반드시 포함시켜줘.

JSON의 필드명은 아래 예시와 **완전히 동일하게 유지**하고, **추가 설명 없이 JSON 객체만 출력**해줘.

예시:
{{
  "title": "레시피 제목",
  "description": "레시피 설명",
  "ingredients": [
    {{
      "name": "재료명",
      "unit": "단위",
      "amount": "수량",
      "shop_url": "구매링크(선택사항)",
      "ingredient_id": ""
    }}
  ],
  "steps": [
    {{
      "description": "조리 단계 설명",
      "isImportant": false
    }}
  ],
  "videourl": "유튜브 링크"
}}

중요한 규칙:
- steps는 최대 10단계로 제한
- 각 단계의 description은 핵심만 담되 간결하게 작성
- 재료로 추출된 모든 항목은 **적어도 1회 이상 조리 단계에서 사용되도록** 반영할 것
- isImportant 필드는 모든 단계에서 반드시 false로 설정해야 함 (true로 설정하지 마세요)
- 모든 조리 단계의 isImportant 값은 false여야 합니다

유튜브 링크: {youtube_url}
자막:
{transcript}"""

            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "당신은 요리 레시피 분석 전문가입니다. 주어진 텍스트에서 레시피 정보를 추출하여 JSON 형태로 반환해주세요."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1200,
                temperature=0.2
            )
            
            recipe_json = response.choices[0].message.content.strip()
            
            print(f"[generate-recipe] GPT 응답 받음")
            
            # JSON 파싱 검증
            try:
                # 코드블록 제거
                if recipe_json.startswith('```'):
                    import re
                    recipe_json = re.sub(r'^```(json)?', '', recipe_json, flags=re.IGNORECASE)
                    recipe_json = re.sub(r'```$', '', recipe_json).strip()
                
                parsed_recipe = json.loads(recipe_json)
                print(f"[generate-recipe] JSON 파싱 성공")
                
                return {
                    "success": True,
                    "transcript": transcript,
                    "recipe": parsed_recipe
                }
                
            except json.JSONDecodeError as e:
                print(f"[generate-recipe] JSON 파싱 실패: {e}")
                return {
                    "success": False,
                    "error": "GPT 응답에서 JSON 파싱에 실패했습니다.",
                    "raw_response": recipe_json,
                    "transcript": transcript
                }
                
    except Exception as e:
        print(f"[generate-recipe] 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=f"레시피 생성 중 오류가 발생했습니다: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 