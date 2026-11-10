# REA Video Evidence

[English](README.md) · [繁體中文](README.zh-TW.md) · [日本語](README.ja.md) · [한국어](README.ko.md)

영상의 샷, 화면 텍스트, 오디오 신호와 제작 방식에 대한 가설을 정리하는 CLI 및 에이전트 스킬입니다. 필요한 시간대의 근거를 찾아 전체 보고서를 에이전트에 전달하는 부담을 줄입니다.

이 프로젝트는 [JuneYaooo/rea-video](https://github.com/JuneYaooo/rea-video)의 commit `d2fb1e06373a7ecc9379545591ac3904f154b8c9`를 바탕으로 독립적으로 유지하는 파생 프로젝트입니다. Apache-2.0 라이선스와 원저자 표시를 유지합니다. 변경 범위는 [UPSTREAM.md](UPSTREAM.md)를 참고하세요.

## 이 버전의 추가 기능

- **필요한 근거 조회**: 기존 분석을 시간 범위 또는 문자열로 검색하고 타임스탬프와 출처를 포함한 JSON을 반환합니다.
- **검토 대기 목록**: 에이전트 검토가 적용되지 않은 샷을 찾고 불확실한 샷부터 우선 표시하며 페이지별 조회를 지원합니다.
- **명확한 상태 구분**: OCR, 도구 근거, 에이전트 검토, 외부 VLM 상태, 누락 이미지와 기록되지 않은 청취 확인을 분리합니다.
- **Windows 유니코드 경로 지원**: 한글 등이 포함된 경로에서도 스토리보드, 요소 및 스티커 이미지를 보존합니다.
- **이식 가능한 스킬**: 기존 스킬을 덮어쓰지 않고 Codex, Claude Code 등에 설치할 수 있습니다.

샷 감지, 제작 방식 분류, OCR, 보고서와 재제작 계획은 상위 프로젝트에서 이어받았습니다. 분류 점수는 가설이며 실제 제작 출처의 증명이 아닙니다.

## 0.2 개선 사항

검토 답변을 원본 영상·샷·이미지에 연결하여 다른 영상의 답변과 잘못된 확률을 거부합니다. OCR은 전체 분석의 호출 상한과 실패 상태를 기록합니다. SRT/VTT 및 선택적 로컬 ASR을 통해 발화와 화면 텍스트를 분리하여 검색합니다. `doctor`, `inspect`, `chapters --resume`, `validate-claims`로 환경 진단, 필요한 구간의 추가 추출, 재개 가능한 긴 영상 색인 및 인용 검증을 수행합니다. 보관하는 전체 크기 샷 이미지를 제한하고 상위 프로젝트의 영어 표기 수정도 반영했습니다.

[명령·호환성·제한](docs/workflows.md)을 참고하세요. chapters는 표본 근거 색인이며 전체 분류의 재개 기능이 아닙니다. ASR은 기존 로컬 모델이 필요하고 자동으로 다운로드하지 않습니다. 기본 보고서 언어는 여전히 zh/en입니다.

## 설치

Python 3.10 이상과 PATH에 등록된 FFmpeg／FFprobe가 필요합니다. 상위 프로젝트와 `rea_video` 모듈 및 `rea-video` 명령을 공유하므로 별도 환경을 사용하세요.

```sh
git clone https://github.com/teateatea03/rea-video-evidence.git
cd rea-video-evidence
python -m venv .venv
```

macOS／Linux에서는 `source .venv/bin/activate`, Windows PowerShell에서는 `.venv\Scripts\Activate.ps1`로 활성화합니다. 실행 정책으로 활성화가 차단되면 시스템 정책을 바꾸는 대신 환경 안의 Python／CLI를 전체 경로로 실행하세요.

```sh
python -m pip install -e ".[dev]"
rea-video --help
python scripts/install_skill.py --agent codex
```

Python 배포 패키지 이름은 `rea-video-evidence`, CLI 이름은 `rea-video`입니다. 설치 스크립트는 스킬만 복사하며 PATH나 CLI를 변경하지 않습니다. 기존 대상은 덮어쓰지 않습니다. `--agent claude`, `--agent agents` 또는 `--dest`를 지정할 수도 있습니다.

OCR은 선택 사항입니다. RapidOCR가 요구하는 `opencv-python`은 headless OpenCV와 파일이 충돌하므로 별도 환경 안에서 다음을 실행하세요.

```sh
python -m pip install -e ".[ocr]"
python -m pip uninstall -y opencv-python
python -m pip install --force-reinstall --no-deps "opencv-python-headless>=4.8,<5"
```

이 상위 프로젝트의 우회 방법을 사용하면 headless가 `cv2`를 제공하더라도 `pip check`에 RapidOCR 의존성 메타데이터 경고가 남습니다. 실제 OCR 동작을 확인하고 의존성 검사가 완전히 통과했다고 표현하지 마세요.

## 사용

```sh
rea-video decompose "reference.mp4" -o "out/reference-01" --no-vlm --lang en
rea-video summary "out/reference-01/breakdown.json"
rea-video evidence "out/reference-01" --start 3.5 --end 8 --limit 4
rea-video evidence "out/reference-01" --query "상품" --limit 4
rea-video evidence "out/reference-01" --pending --limit 4
```

`evidence`는 읽기 전용입니다. 재디코딩, 모델 호출, 인증 정보 로드 및 영구 메모리 쓰기를 하지 않습니다. 기존 OCR／도구／검토 텍스트와 가져온 자막을 출처별로 검색합니다. 조회 중에 음성 인식이나 관찰하지 않은 화면의 의미 검색을 수행하지 않습니다. 결과가 없다고 영상에 해당 내용이 없다는 뜻은 아닙니다.

시간 범위는 `[start,end)`입니다. `pagination.next_offset`을 `--offset`으로 전달하면 다음 페이지를 조회할 수 있습니다. 이미지를 확인할 수 있는 에이전트는 다음을 사용합니다.

```sh
rea-video review "out/reference-01"
# 실제 이미지를 보고 확인한 샷만 review_answers.json에 작성합니다.
rea-video apply-review "out/reference-01" --by your-agent
```

HTML／Markdown 보고서, JSON, 샷 이미지와 사용 가능한 자막／오디오 파일을 출력합니다. 첫 음원 분리 시 약 67 MB의 UVR ONNX 모델을 로컬 캐시에 다운로드합니다. 외부 VLM은 선택 사항이며 별도 설정이 필요하고 비용이 발생할 수 있습니다. 인증 정보는 저장소에 넣지 마세요.

## 제한과 검증

도구의 보고서 생성 언어는 `zh`와 `en`입니다. 네 언어 README가 한국어／일본어 보고서의 기본 지원을 뜻하지는 않습니다. 에이전트 응답은 사용자의 언어에 맞출 수 있습니다.

프레임 주기만으로 AI 제작 여부를 증명할 수 없습니다. OCR은 음성 전사문이 아니며 이미지 파일의 존재는 시각 검토의 증명이 아닙니다. 디코딩 성공이나 오디오 신호는 말소리의 명료도 또는 음악 출처를 보장하지 않습니다. 적용된 검토는 샘플 프레임에 대한 기록이며 전체 영상 시청을 의미하지 않습니다. 새로운 분류 정확도를 주장하지 않습니다.

```sh
python -m pytest -q
```

테스트는 생성된 자료와 격리된 메모리를 사용합니다. 참고 영상, 사용자 보고서, 모델 가중치, 인증 정보와 개별 컴퓨터의 유지보수 로그는 배포하지 않습니다.

## 링크와 출처

- [GitHub](https://github.com/teateatea03/rea-video-evidence)／[GitLab.com](https://gitlab.com/angeltea01/rea-video-evidence)
- [근거 데이터 계약](docs/evidence.md)／[에이전트 스킬](skills/rea-video/SKILL.md)
- [변경 이력](CHANGELOG.md)／[기여 방법](CONTRIBUTING.md)
- [상위 프로젝트와 참고 자료](UPSTREAM.md)／[라이선스](LICENSE)／[저작권 표시](NOTICE)

소유자는 별도의 로컬 GitLab 미러를 유지할 수 있습니다. 접근 범위는 소유자의 네트워크 및 접근 정책에 따릅니다.
