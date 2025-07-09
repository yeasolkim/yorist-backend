# Yorist Backend API

유튜브 쇼츠에서 레시피를 자동 생성하는 FastAPI 백엔드 서버입니다.

## 기능

- 유튜브 쇼츠 URL을 받아서 오디오 다운로드
- Whisper를 사용한 음성→텍스트 변환
- OpenAI GPT를 사용한 레시피 JSON 생성

## API 엔드포인트

### GET /generate-recipe
유튜브 쇼츠에서 레시피를 생성합니다.

**Query Parameters:**
- `youtube_url` (string, required): 유튜브 쇼츠 URL

**Response:**
```json
{
  "success": true,
  "transcript": "추출된 자막 텍스트",
  "recipe": {
    "title": "레시피 제목",
    "description": "레시피 설명",
    "ingredients": [...],
    "steps": [...],
    "videourl": "유튜브 링크"
  }
}
```

## 환경 변수

- `OPENAI_API_KEY`: OpenAI API 키 (필수)

## 로컬 실행

1. 의존성 설치:
```bash
pip install -r requirements.txt
```

2. 환경 변수 설정:
```bash
export OPENAI_API_KEY="your-openai-api-key"
```

3. 서버 실행:
```bash
python main.py
```

또는:
```bash
uvicorn main:app --reload
```

## Railway 배포

1. GitHub에 코드 푸시
2. Railway에서 새 프로젝트 생성
3. GitHub 저장소 연결
4. 환경 변수 설정:
   - `OPENAI_API_KEY`: OpenAI API 키
5. 배포 완료 후 URL 확인

## 주의사항

- Whisper 모델은 첫 실행 시 다운로드됩니다 (약 1GB)
- 처리 시간은 영상 길이에 따라 1-3분 정도 소요될 수 있습니다
- Railway의 무료 플랜은 월 사용량 제한이 있습니다 