# CareFull Raspberry Pi - Management & Session Recovery Script
# cli 재실행 시 종전 작업 확인 및 세션 복구
# raspberry/manage.ps1 로 실행

function Show-Header {
    Clear-Host
    Write-Host "===============================================" -ForegroundColor Cyan
    Write-Host "   CareFull Project - Raspberry Pi Module    " -ForegroundColor Cyan
    Write-Host "===============================================" -ForegroundColor Cyan
    Write-Host "라즈베리파이 전용 세션 복구 및 진행 상황 확인 스크립트입니다."
    Write-Host ""
}

function Show-LatestLog {
    $logPath = "md/result.md"
    if (Test-Path $logPath) {
        Write-Host " [최근 진행 상황 (md/result.md)] " -BackgroundColor DarkBlue -ForegroundColor White
        Get-Content $logPath | Select-Object -Last 15
    } else {
        Write-Warning "로그 파일을 찾을 수 없습니다: $logPath"
    }
    Write-Host ""
}

function Show-Menu {
    Write-Host "1. 최근 로그 확인 (Full)"
    Write-Host "2. 라즈베리파이 메인 실행 (main.py)"
    Write-Host "3. 현재 상황 요약 및 제안 (AI)"
    Write-Host "q. 종료"
    Write-Host ""
}

# Main Loop
while ($true) {
    Show-Header
    Show-LatestLog
    Show-Menu
    
    $choice = Read-Host "원하는 작업의 번호를 입력하세요"
    
    switch ($choice) {
        "1" {
            if (Test-Path "md/result.md") {
                Get-Content "md/result.md" | Out-Host
            }
            Pause
        }
        "2" {
            $date = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
            Write-Host "라즈베리파이 모듈 실행 및 로그 기록 중..." -ForegroundColor Green
            
            # 로그 파일에 실행 시점 기록
            echo "`n---`n## [ $date ] 실행 로그" >> md/result.md
            echo '```bash' >> md/result.md
            
            # 실행 결과를 화면에도 보여주고, 파일에도 동시에 기록 (Tee-Object)
            python main.py 2>&1 | Tee-Object -Append md/result.md
            
            echo '```' >> md/result.md
            Pause
        }
        "3" {
            Write-Host "AI에게 현재 상황 보고 중..." -ForegroundColor Magenta
            if (Test-Path "md/result.md") {
                $context = Get-Content "md/result.md" | Select-Object -Last 30
                $context | gemini "위 내용은 내 프로젝트의 라즈베리파이 모듈 최근 로그야. 현재 진행 상황을 요약하고, 다음 단계로 무엇을 구현하면 좋을지 제안해줘."
            } else {
                Write-Warning "분석할 로그 파일이 없습니다."
            }
            Pause
        }
        "q" {
            break
        }
        default {
            Write-Host "잘못된 입력입니다." -ForegroundColor Red
            Start-Sleep -Seconds 1
        }
    }
}
