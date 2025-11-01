# LLM Provider Decision Matrix

**Date:** Oct 31, 2025  
**Current Status:** Using llama.cpp 1.5B local model

---

## 🎯 Recommendation: **Stick with llama.cpp for POC**

---

## Current Setup: llama.cpp 1.5B

### ✅ Advantages
- **FREE** - No API costs
- **PRIVATE** - No data leaves your network
- **Fast** - No network latency
- **Reliable** - No rate limits or downtime
- **Production-ready** - Already working

### ❌ Limitations
- **5-6 steps** - Model too small for 10-12 steps
- **Quality** - Basic reasoning capability
- **No web search** - Cannot retrieve external knowledge

### 📊 Quality Rating: ⭐⭐☆☆☆ (2/5)

---

## Alternative: Perplexity API

### Sonar Pricing Options
Based on [Perplexity pricing](https://docs.perplexity.ai/getting-started/pricing#request-pricing):

1. **Sonar** - $1/M input + $1/M output
   - ~$0.006 per runbook
   - Better than 1.5B but may still struggle

2. **Sonar Pro** - $3/M input + $15/M output
   - ~$0.05 per runbook
   - High quality, should handle 10-12 steps

3. **Sonar Reasoning Pro** - $2/M input + $8/M output
   - ~$0.03 per runbook
   - Multi-step reasoning with search

### ✅ Advantages
- **Higher quality** - Likely 70B+ parameters
- **More steps** - Can generate 10-12 comprehensive steps
- **Web search** - Real-time knowledge retrieval
- **Better reasoning** - Advanced understanding

### ❌ Disadvantages
- **COSTS** - $6-50/month for 1000 runbooks
- **PRIVACY** - Data leaves network
- **DEPENDENCY** - Requires internet
- **LATENCY** - Network delays

### 📊 Quality Rating: ⭐⭐⭐⭐☆ (4/5)

---

## 💰 Cost Analysis

### Monthly Runbook Volume
| Volume | Sonar | Sonar Pro | Sonar Reasoning Pro |
|--------|-------|-----------|---------------------|
| 100    | $0.60 | $5        | $3                  |
| 1,000  | $6    | $50       | $30                 |
| 10,000 | $60   | $500      | $300                |

### Current Setup
- **Cost:** $0 (just electricity)
- **Runbooks:** ~5-6 steps each
- **Quality:** Acceptable for POC

---

## 🤔 Decision Framework

### Use llama.cpp 1.5B if:
- ✅ You're in POC/development phase
- ✅ Privacy is important (internal troubleshooting data)
- ✅ Budget is tight
- ✅ 5-6 steps are sufficient for demos
- ✅ You want fast iteration without costs

### Consider Perplexity API if:
- ❓ Production users need comprehensive 10-12 step runbooks
- ❓ Quality matters more than privacy
- ❓ Budget allows $30-50/month
- ❓ Web knowledge search adds value
- ❓ You're ready for production launch

---

## 🔄 Alternative: Local Larger Model

**Option 3:** Upgrade to local llama.cpp 7B or 13B

### ✅ Advantages
- Still **FREE** (no API costs)
- **PRIVATE** (stays local)
- Better quality than 1.5B
- Should get 8-10 steps
- No per-runbook costs

### ❌ Disadvantages
- Requires 8-16GB RAM
- Slower inference
- Still limited vs Perplexity quality

---

## 🎯 Current Decision

**For now:** Continue with llama.cpp 1.5B

**Reasoning:**
1. POC is working - no need to change mid-flight
2. Free and private - no barriers to iteration
3. 5-6 steps adequate for proof of concept
4. Focus on workflow and feature completion
5. Perplexity code already added - easy to switch later

**When to reconsider:**
- Production launch approaching
- Users demand more comprehensive runbooks
- Budget allows Perplexity costs
- Privacy concerns are lower

---

## 🔧 Implementation Status

✅ **Perplexity integration code added**  
✅ **Auto-detection via environment variable**  
✅ **Switch providers with single env var change**

**To activate Perplexity later:**
```bash
# In docker-compose.yml or .env
PERPLEXITY_API_KEY=your_api_key_here

# Or when running docker-compose
PERPLEXITY_API_KEY=xxx docker-compose up
```

---

**Next Steps:** Continue improving prompts and workflow with current setup.


