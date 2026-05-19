$ErrorActionPreference = "Stop"

$token = Read-Host "Paste GitHub token"
$owner = "jolleyleads"

$headers = @{
    Authorization = "Bearer $token"
    Accept = "application/vnd.github+json"
    "X-GitHub-Api-Version" = "2022-11-28"
    "User-Agent" = "Repo-Polisher-PowerShell"
}

$repoConfig = @{
    "ai-ops-command-center" = @{
        description = "Full-stack AI operations dashboard with Flask, automation APIs, job intelligence, email triage, Make.com workflows, resume outreach, and Render deployment."
        homepage = "https://ai-ops-command-center.onrender.com"
        topics = @("python","flask","ai","automation","make-com","api","render","backend","job-search","email-automation","workflow-automation","sqlite","machine-learning","ai-engineering","nlp")
    }

    "ai-lead-intelligence-command-center" = @{
        description = "Signal-based AI lead intelligence platform that scores businesses for automation pain, revenue leaks, hiring strain, follow-up issues, and workflow bottlenecks."
        homepage = "https://ai-lead-intelligence-command-center.onrender.com"
        topics = @("python","flask","ai","automation","lead-generation","crm","make-com","render","backend","sales-automation","workflow-automation","sqlite","prospecting","business-intelligence")
    }

    "electrical-license-lead-command-center" = @{
        description = "Lead intelligence platform for identifying, scoring, and managing high-intent contractor leads seeking licensed electrical contractor coverage and outreach automation."
        homepage = "https://electrical-license-lead-command-center.onrender.com"
        topics = @("python","flask","automation","crm","lead-generation","contractor-leads","make-com","sqlite","render","ai","workflow-automation","sales-automation")
    }

    "synthetic-voice-agent-command-center" = @{
        description = "Voice-enabled GPT-style AI assistant using Flask, OpenAI, speech recognition, text-to-speech, tool routing, and AI Ops Command Center integrations."
        homepage = ""
        topics = @("python","flask","openai","voice-ai","speech-recognition","text-to-speech","ai-agent","automation","api","render","assistant","workflow-automation")
    }

    "ml-remote-job-finder" = @{
        description = "Flask backend and Make.com-ready API for searching remote AI, ML, NLP, Python, and automation jobs across multiple public job sources."
        homepage = "https://ml-remote-job-finder.onrender.com"
        topics = @("python","flask","api","automation","make-com","remote-jobs","machine-learning","ai","render","backend","job-search","nlp")
    }

    "spam-classifier-nlp" = @{
        description = "Deployed NLP spam classifier with Flask API, Make.com Gmail automation, workflow screenshots, and Render deployment."
        homepage = "https://spam-classifier-nlp.onrender.com"
        topics = @("python","flask","machine-learning","nlp","spam-classifier","api","make-com","gmail","automation","render","scikit-learn")
    }

    "home-predictor" = @{
        description = "Flask-based machine learning regression app for home price prediction and real estate valuation."
        homepage = "https://home-predictor.onrender.com"
        topics = @("python","flask","machine-learning","regression","scikit-learn","pandas","numpy","real-estate","render","web-app")
    }

    "ai-outreach-automation-system" = @{
        description = "AI outreach automation system using Make.com, OpenAI, Hunter.io, Gmail drafts, lead enrichment, and human-in-the-loop approval workflows."
        homepage = ""
        topics = @("ai","automation","make-com","openai","hunter-io","gmail","lead-generation","workflow-automation","api","sales-automation")
    }

    "ML-PIPELINE-INFRASTRUCTURE" = @{
        description = "Machine learning pipeline infrastructure project for preprocessing, feature engineering, model training, evaluation, and deployment-oriented ML workflows."
        homepage = ""
        topics = @("python","machine-learning","ml-pipeline","scikit-learn","pandas","numpy","feature-engineering","model-training","mlops","automation")
    }

    "mltubular" = @{
        description = "API-first machine learning scaffold with FastAPI-style architecture, feature engineering, RandomForest training, and RAG-ready backend structure."
        homepage = ""
        topics = @("python","machine-learning","fastapi","api","rag","embeddings","scikit-learn","backend","ai","mlops")
    }

    "jolleyleads" = @{
        description = "GitHub profile README for Matthew Jolley's AI automation, applied machine learning, and workflow systems portfolio."
        homepage = "https://github.com/jolleyleads"
        topics = @("profile","ai","automation","machine-learning","portfolio","github-readme")
    }
}

Write-Host "Checking GitHub token..."
$userCheck = Invoke-RestMethod -Uri "https://api.github.com/user" -Headers $headers -Method Get
Write-Host "Authenticated as $($userCheck.login)"
Write-Host ""

$updated = @()
$failed = @()

foreach ($name in $repoConfig.Keys) {
    $config = $repoConfig[$name]

    try {
        Write-Host "Updating $name..."

        $patch = @{
            description = $config.description
        }

        if ($config.homepage -and $config.homepage.Trim().Length -gt 0) {
            $patch.homepage = $config.homepage
        }

        $patchJson = $patch | ConvertTo-Json -Depth 10

        Invoke-RestMethod `
            -Uri "https://api.github.com/repos/$owner/$name" `
            -Headers $headers `
            -Method Patch `
            -Body $patchJson `
            -ContentType "application/json" | Out-Null

        $topicsJson = @{
            names = $config.topics
        } | ConvertTo-Json -Depth 10

        Invoke-RestMethod `
            -Uri "https://api.github.com/repos/$owner/$name/topics" `
            -Headers $headers `
            -Method Put `
            -Body $topicsJson `
            -ContentType "application/json" | Out-Null

        $updated += $name
        Write-Host "Updated $name"
    }
    catch {
        $failed += "${name} - $($_.Exception.Message)"
        Write-Host "FAILED ${name}: $($_.Exception.Message)"
    }
}

Write-Host ""
Write-Host "=============================="
Write-Host "REPO POLISH COMPLETE"
Write-Host "=============================="

Write-Host ""
Write-Host "Updated repos:"
$updated | ForEach-Object { Write-Host " - $_" }

Write-Host ""
Write-Host "Failed repos:"
if ($failed.Count -eq 0) {
    Write-Host " None"
} else {
    $failed | ForEach-Object { Write-Host " - $_" }
}

Write-Host ""
Write-Host "Refresh:"
Write-Host "https://github.com/jolleyleads"