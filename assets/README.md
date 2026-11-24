# 화면 이미지와 스타일

- `sports-hero.png`: 홈의 서비스 소개용 대표 이미지. 내장 `image_gen` 도구로 새로 생성했습니다.
  특정 실제 시설을 촬영한 사진이나 참고 사이트의 사진이 아닙니다.
- `site.css`: 홈, 메뉴, 시설 탐색 카드와 모바일 레이아웃 스타일.
- `seoul-districts-2015.geojson`: 현황 탭의 자치구별 통계 지도 전용 경계.
  JUSO의 2015년 서울 시군구 자료를 변환·단순화한 southkorea/seoul-maps의 파일을
  수정 없이 포함했습니다. 시설 자료의 기준 연도와는 별개이며 위치 탐색에는 사용하지 않습니다.
  - 원본: https://github.com/southkorea/seoul-maps/blob/dbb1dcde2e3c9937684c5a44ab9301888ad63ee6/juso/2015/json/seoul_municipalities_geo_simple.json
  - 기여자: Lucy Park 및 southkorea/seoul-maps contributors.
  - 라이선스: 원본 README의 Apache v2.0. 전문은 [seoul-maps-LICENSE.txt](licenses/seoul-maps-LICENSE.txt)에 포함했습니다.
- 디자인 참고: [국민체육진흥공단](https://www.kspo.or.kr/kspo/main/main.do),
  [한국체육산업개발](https://www.ksponco.or.kr/). 상단 메뉴·대형 체육 이미지·서비스 진입 구조를 참고했습니다.
  로고와 문구, 이미지를 복제하지 않았습니다.

## 이미지 생성 프롬프트

```text
Use case: photorealistic-natural. Asset type: original panoramic website hero photograph for a Korean public sports facility discovery site called Seoul Sports Map. Scene: a bright modern neighborhood public sports park in Seoul, outdoor blue and teal tennis courts with crisp white lines, two adult recreational tennis players on the right side in natural candid action, a running path and leafy trees beyond, very subtle urban skyline. Wide panoramic composition around 3:1, usable calmer negative space across left half for HTML heading overlay. Fresh blue sky, inviting morning daylight, premium editorial photography, realistic human anatomy and court perspective, deep greens and vivid sky blue, energetic but calm. No text, no letters, no logos, no watermarks, no branding, no infographic or UI. This is illustrative scenery, not a depiction of a specific named facility. Save an original full-bleed sports hero asset suitable for a responsive Korean public service homepage.
```
