# Aura AI 학습 메모리 최적화 가이드 (Windows)

## 목표와 현실적인 한계

현재 PC는 RAM 약 16 GB이며, PyTorch는 CPU 전용 빌드라 CUDA GPU를 사용할 수 없는 상태로 확인되었다. 작업 관리자에서 메모리 95%, 디스크 100%가 보인다면 학습을 시작하기 전에 여유 공간부터 확보해야 한다. 메모리 사용량 30%는 이 PC에서 약 4.8 GB 수준(Windows가 인식하는 RAM 용량에 따라 다름)이지만, Windows·브라우저·Discord 등 다른 프로그램의 메모리까지 합산한 값이므로 코드만으로 30%를 보장할 수는 없다.

## 이번 최적화 내용

- `data/train.txt` 전체를 문자열과 토큰 리스트로 RAM에 복제하지 않는다.
- UTF-8 파일을 memory-map으로 열고 학습에 필요한 작은 바이트 배치만 읽는다.
- 기본 batch size를 16에서 2로 낮춘다. RAM이 빠듯하면 1로 설정한다.
- CPU 스레드 수를 기본 2개로 제한한다.
- PyTorch의 `scaled_dot_product_attention`을 사용해 attention 연산을 최적화한다.
- 기본 500 step마다 임시 파일에 저장한 뒤 체크포인트를 원자적으로 교체한다. 중간에 프로세스가 중단되어도 이전 체크포인트를 최대한 보존한다.
- 원본 데이터는 삭제하지 않는다.

## 1. 학습 전에 작업 관리자 확인

1. Ctrl + Shift + Esc를 눌러 작업 관리자를 연다.
2. 프로세스 탭에서 메모리 열을 눌러 큰 순서로 정렬한다.
3. 사용하지 않는 브라우저 탭과 무거운 앱을 직접 종료한다. 저장하지 않은 작업은 먼저 저장한다.
4. 메모리가 계속 85~90% 이상이거나 디스크가 100%로 고정되어 있으면 학습을 시작하지 말고 먼저 원인을 해결한다.
5. `data/train.txt`가 있는 드라이브에 체크포인트와 Windows 페이지 파일을 위한 여유 공간을 확보한다. 학습 데이터가 수십 GB라면 여유 공간을 최소한 그 파일 크기보다 충분히 크게 잡는다.

## 2. 가상환경 활성화

PowerShell을 열고 아래 명령을 순서대로 실행한다.

```powershell
cd C:\Users\L\Downloads\Koharu\Aura-AI
.\.venv\Scripts\Activate.ps1
```

프롬프트 앞에 `(.venv)`가 보이면 활성화된 것이다. 활성화가 차단되면 현재 PowerShell 창에서만 다음을 실행하고 다시 활성화한다.

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\.venv\Scripts\Activate.ps1
```

## 3. 3-step 테스트부터 실행

실제 모델 체크포인트를 덮어쓰지 않고 짧은 테스트를 하려면 다음을 실행한다.

```powershell
python -m aura.train --data data/train.txt --output "$env:TEMP\aura-test.pt" --steps 3 --batch-size 1 --threads 1 --log-every 1 --checkpoint-every 0 --device cpu
```

정상이라면 `Device: cpu`, `RAM optimization: corpus is memory-mapped`와 step 손실값, `Checkpoint saved`가 출력된다. 이 테스트는 파이프라인 확인용일 뿐 실제 학습이 충분하다는 뜻이 아니다.

## 4. 저메모리 학습 시작

먼저 메모리와 디스크 여유가 충분한지 확인한 후 아래 명령을 실행한다.

```powershell
python -m aura.train --data data/train.txt --steps 3000 --batch-size 1 --threads 1 --log-every 25 --checkpoint-every 250 --device cpu
```

이 설정은 메모리를 낮추고 CPU의 동시 작업 수를 줄이는 대신 학습 속도가 느려질 수 있다. `--steps 3000`은 3000회의 optimizer update를 의미하며, 3000개 파일이나 3000 epoch를 뜻하지 않는다.

RAM 사용량이 안정적이고 시스템이 반응하는 경우에만 조금씩 높인다.

```powershell
python -m aura.train --data data/train.txt --steps 3000 --batch-size 2 --threads 2 --log-every 50 --checkpoint-every 250 --device cpu
```

한 번에 batch size와 threads를 모두 올리지 말고, 하나씩 바꾸어 작업 관리자에서 비교한다. 이 프로젝트는 CPU 전용 PyTorch 빌드이므로 `--device cuda`는 현재 환경에서 사용할 수 없다. CUDA를 쓰려면 호환되는 NVIDIA GPU와 그 GPU·드라이버에 맞는 PyTorch 빌드가 필요하다.

## 5. 학습 중 관찰할 지표

- **Memory**: 계속 증가하여 90% 이상에 머무르면 중단을 고려한다.
- **Disk**: 100% 고정이면 페이지 파일, 백신 검사, 다른 프로세스, 데이터 읽기 병목을 확인한다.
- **Train loss**: 학습 배치에서 다음 바이트를 예측하는 손실이다.
- **Validation loss**: 학습에서 분리한 후반부 데이터에 대한 지표다.
- **시간/step**: CPU 전용 모델은 데이터와 CPU 상태에 따라 오래 걸릴 수 있다.

손실이 내려가는 것은 모델이 학습 데이터의 패턴을 어느 정도 맞추기 시작했다는 뜻일 뿐, 대화 품질·사실성·안전성의 보증이 아니다. 검증 손실이 계속 나빠지면 과적합, 데이터 중복, 데이터 순서 또는 학습률을 점검한다.

## 6. 중단과 재시작

현재 학습기는 중간 체크포인트를 저장하지만, 아직 체크포인트에서 optimizer 상태를 복구해 이어서 학습하는 `--resume` 기능은 없다. 중단 후 실행하면 기본적으로 새 모델 초기화부터 시작한다. 따라서 긴 학습 중에는 250 step 간격 저장을 사용해 최신 결과를 보존하되, 해당 체크포인트에서 학습이 이어진다고 가정하지 않는다. 다음 개선 작업은 optimizer state를 저장하고 재개 기능을 추가하는 것이다.

중단하려면 터미널에서 Ctrl+C를 누른다. 파일 저장 중일 때는 가능하면 저장 완료 메시지가 나온 뒤 종료한다.

## 7. 데이터 용량과 디스크 100% 문제

memory-map은 파일 전체를 Python 문자열과 토큰 리스트로 복제하는 문제를 해결하지만, 디스크 읽기/쓰기 자체를 없애는 기능은 아니다. 원본 파일이 HDD에 있거나 Windows가 메모리 압박으로 페이지 파일을 자주 사용하면 디스크 사용률이 높을 수 있다.

- 학습 데이터 파일을 SSD에 두면 무작위 읽기가 더 나을 수 있다.
- 출처 원본 ZIP을 반복적으로 풀어 임시 파일을 만들지 않는다.
- `data/source`는 학습 중 삭제하지 않는다.
- 임시 체크포인트와 원본 데이터가 차지하는 용량을 먼저 확인한다.
- 디스크 여유 공간이 매우 적으면 학습을 시작하지 않는다.

## 8. 안전한 권장 순서

1. RAM과 디스크 여유 확인.
2. 3-step 테스트 실행.
3. batch 1, threads 1로 저메모리 학습 시작.
4. 10~15분 동안 메모리·디스크 추이를 관찰.
5. 안정적이면 계속 학습하고, 불안정하면 중단 후 원인을 해결.
6. 학습 후 체크포인트를 로드해 API 테스트.
7. API가 정상 응답할 때만 Render 배포를 검토.
8. 데이터 출처와 이용 조건을 확인하기 전에는 원본을 삭제하지 않는다.

## 중요

이 최적화는 RAM을 덜 쓰게 하는 방향이다. 현재 모델은 약 840,704 파라미터의 소형 Transformer이고 CPU 전용 실행 환경이다. 메모리 사용량을 줄이는 것만으로 대형 언어 모델 수준의 능력이 생기지는 않는다. 실제 대화 모델로 발전시키려면 충분한 학습 데이터, 더 큰 모델, 평가 체계와 훨씬 더 많은 계산 자원이 필요하다.
