# Test Ollama Connection from Host
Write-Host "=== Testing Ollama Connection ===" -ForegroundColor Cyan

# Test 1: Check if Ollama is running
Write-Host "`n1. Checking if Ollama is running..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
        Write-Host "   ✓ Ollama is running on port 11434" -ForegroundColor Green
        $models = ($response.Content | ConvertFrom-Json).models
        Write-Host "   ✓ Found $($models.Count) model(s)" -ForegroundColor Green
        if ($models.Count -gt 0) {
            Write-Host "   Models:" -ForegroundColor Cyan
            foreach ($model in $models) {
                Write-Host "     - $($model.name)" -ForegroundColor White
            }
        } else {
            Write-Host "   ⚠ No models found! Run: ollama pull llama3.2" -ForegroundColor Yellow
        }
    }
} catch {
    Write-Host "   ✗ Ollama is NOT running or not accessible" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "   Solution: Start Ollama with 'ollama serve' or check Windows Services" -ForegroundColor Yellow
    exit 1
}

# Test 2: Check OpenAI-compatible endpoint
Write-Host "`n2. Testing OpenAI-compatible endpoint..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:11434/v1/models" -UseBasicParsing -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
        Write-Host "   ✓ OpenAI-compatible endpoint is working" -ForegroundColor Green
        $data = $response.Content | ConvertFrom-Json
        if ($data.models) {
            $modelName = $data.models[0].model
            Write-Host "   ✓ Model available: $modelName" -ForegroundColor Green
        }
    }
} catch {
    Write-Host "   ✗ OpenAI-compatible endpoint failed" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 3: Test chat completion
Write-Host "`n3. Testing chat completion..." -ForegroundColor Yellow
try {
    $modelName = "llama3.2"
    $payload = @{
        model = $modelName
        messages = @(
            @{
                role = "user"
                content = "Say hello in one word"
            }
        )
        max_tokens = 10
    } | ConvertTo-Json

    $response = Invoke-WebRequest -Uri "http://localhost:11434/v1/chat/completions" `
        -Method POST `
        -ContentType "application/json" `
        -Body $payload `
        -UseBasicParsing `
        -TimeoutSec 30

    if ($response.StatusCode -eq 200) {
        $data = $response.Content | ConvertFrom-Json
        $content = $data.choices[0].message.content
        if ($content -and $content.Trim()) {
            Write-Host "   ✓ Chat completion working! Response: '$content'" -ForegroundColor Green
        } else {
            Write-Host "   ✗ Chat completion returned empty response" -ForegroundColor Red
            Write-Host "   This is the issue! Check Ollama logs or try a different model" -ForegroundColor Yellow
        }
    }
} catch {
    Write-Host "   ✗ Chat completion failed" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        Write-Host "   Response: $responseBody" -ForegroundColor Red
    }
}

# Test 4: Test from Docker container perspective
Write-Host "`n4. Testing connection from Docker container..." -ForegroundColor Yellow
Write-Host "   (This simulates what the backend container sees)" -ForegroundColor Gray
try {
    docker-compose exec -T backend python -c "
import httpx
import asyncio
import sys

async def test():
    base_url = 'http://host.docker.internal:11434'
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Test models endpoint
            resp = await client.get(f'{base_url}/v1/models')
            if resp.status_code == 200:
                data = resp.json()
                models = data.get('data', []) or data.get('models', [])
                if models:
                    model_name = models[0].get('id') or models[0].get('model') or models[0].get('name')
                    print(f'✓ Connected! Model: {model_name}')
                    
                    # Test chat
                    payload = {
                        'model': model_name,
                        'messages': [{'role': 'user', 'content': 'Hi'}],
                        'max_tokens': 5
                    }
                    resp = await client.post(f'{base_url}/v1/chat/completions', json=payload, timeout=30.0)
                    if resp.status_code == 200:
                        data = resp.json()
                        content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
                        if content and content.strip():
                            print(f'✓ Chat working! Response: {content[:50]}')
                        else:
                            print('✗ Chat returned empty response')
                            sys.exit(1)
                    else:
                        print(f'✗ Chat failed: {resp.status_code}')
                        print(resp.text[:200])
                        sys.exit(1)
                else:
                    print('✗ No models found')
                    sys.exit(1)
            else:
                print(f'✗ Connection failed: {resp.status_code}')
                print(resp.text[:200])
                sys.exit(1)
    except Exception as e:
        print(f'✗ Error: {e}')
        sys.exit(1)

asyncio.run(test())
" 2>&1
} catch {
    Write-Host "   ✗ Could not test from Docker container" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n=== Diagnostic Complete ===" -ForegroundColor Cyan
Write-Host "`nIf Ollama is not running, start it with:" -ForegroundColor Yellow
Write-Host "  ollama serve" -ForegroundColor White
Write-Host "`nIf no models are found, pull one with:" -ForegroundColor Yellow
Write-Host "  ollama pull llama3.2" -ForegroundColor White



