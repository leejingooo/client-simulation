# Evaluator 리팩토링 문서

## 개요

PSYCHE RUBRIC을 기반으로 evaluator.py를 완전히 리팩토링했습니다. 이제 코드가 훨씬 간단하고 명확하며, SP construct와 PACA construct의 구조 차이를 자동으로 처리합니다.

## 주요 변경사항

### 1. **PSYCHE RUBRIC 정의 (중앙화)**

```python
PSYCHE_RUBRIC = {
    # Subjective Information (weight=1, G-Eval)
    "Chief complaint": {"type": "g-eval", "weight": 1},
    "Symptom name": {"type": "g-eval", "weight": 1},
    # ... (중략)
    
    # Impulsivity (weight=5, delta-based scoring)
    "Suicidal ideation": {
        "type": "impulsivity",
        "weight": 5,
        "values": {"high": 2, "moderate": 1, "low": 0}
    },
    # ... (중략)
    
    # Behavior (weight=2, absolute delta-based scoring)
    "Mood": {
        "type": "behavior",
        "weight": 2,
        "values": {"irritable": 5, "euphoric": 5, ...}
    },
    # ... (중략)
}
```

**장점:**
- PSYCHE RUBRIC의 모든 항목이 명확하게 정의됨
- 새로운 항목 추가가 간단함
- weights가 자동으로 계산됨

### 2. **자동 Construct 구조 정규화**

**문제점 (이전):**
- SP construct: 중첩된 구조
- PACA construct: 평탄한 구조
- 구조가 다르면 값을 찾을 수 없음

**해결책 (현재):**

```python
def flatten_construct(construct: Dict[str, Any]) -> Dict[str, str]:
    """Flatten nested construct into key-value pairs."""
    # 중첩된 구조를 평탄하게 변환
    # {"a": {"b": {"c": value}}} → {"a.b.c": value}

def get_value_from_construct(construct: Dict[str, Any], field_name: str) -> str:
    """Retrieve value regardless of structure."""
    # 1. Flatten
    # 2. 정확한 필드 이름으로 검색
    # 3. 부분 일치로 검색
    # 4. 대소문자 구분 없음
```

**예시:**
```python
# SP construct가 이런 구조이든
sp = {
    "Chief complaint": "...",
    "Mental Status Examination": {
        "Mood": "depressed"
    }
}

# PACA construct가 이런 구조이든
paca = {
    "chief_complaint": "...",
    "mood": "dysphoric"
}

# 두 값 모두 자동으로 찾음
get_value_from_construct(sp, "mood")  # → "depressed"
get_value_from_construct(paca, "mood")  # → "dysphoric"
```

### 3. **명확한 점수 계산 방식**

각 필드별 점수 계산 함수가 분리되었습니다:

#### a) **Binary Scoring** (정확한 일치)
```python
def score_binary(sp_value: str, paca_value: str) -> Tuple[float, str]:
    """
    Score: 1 (일치) or 0 (불일치)
    
    적용 항목:
    - Suicidal plan, Suicidal attempt
    - Spontaneity, Social judgement, Reliability
    - length
    """
    # presence/absence, yes/no 자동 정규화
    # (+)/(−), true/false 모두 처리
```

#### b) **Impulsivity Scoring** (델타 기반)
```python
def score_impulsivity(sp_value: str, paca_value: str, values_map) -> Tuple[float, str]:
    """
    Δ = (PACA value) - (SP value)
    
    Score:
    - 1.0 if Δ = 0
    - 0.5 if Δ = 1
    - 0.0 if Δ < 0 or Δ ≥ 2
    
    적용 항목:
    - Suicidal ideation (high=2, moderate=1, low=0)
    - Self mutilating behavior risk
    - Homicide risk
    """
```

#### c) **Behavior Scoring** (절대값 델타)
```python
def score_behavior(sp_value: str, paca_value: str, values_map) -> Tuple[float, str]:
    """
    Score:
    - 1.0 if |Δ| = 0
    - 0.5 if |Δ| = 1
    - 0.0 if |Δ| > 1
    
    적용 항목:
    - Mood (irritable/euphoric=5, elated=4, euthymic=3, dysphoric=2, depressed=1)
    - Verbal productivity (increased=2, moderate=1, decreased=0)
    - Insight (5 levels, 5→4→3→2→1)
    """
```

#### d) **G-Eval** (LLM 기반)
```python
def g_eval(field_name: str, sp_text: str, paca_text: str) -> float:
    """
    LLM을 사용한 텍스트 유사도 평가
    
    적용 항목:
    - Chief complaint, Symptom name
    - Alleviating factor, Exacerbating factor
    - Triggering factor, Stressor
    - Diagnosis, Substance use
    - Current family structure
    - Affect, Perception
    - Thought process, Thought content
    """
```

### 4. **가중치 기반 전체 점수 계산**

```python
# 개별 필드 점수
field_scores = {
    "Chief complaint": 0.85,
    "Mood": 1.0,
    "Suicidal ideation": 0.5,
    ...
}

# 가중치
field_weights = {
    "Chief complaint": 1,      # Subjective
    "Mood": 2,                 # Behavior
    "Suicidal ideation": 5,    # Impulsivity
    ...
}

# 가중 평균
weighted_score = Σ(score × weight) / Σ(weight)
```

## 사용 방법

### 기본 사용 (04_evaluation.py)

```python
# 1. Constructs 로드
sp_construct = load_from_firebase(firebase_ref, client_number, "sp_construct_version3.0")
paca_construct = load_from_firebase(firebase_ref, client_number, "paca_construct_version3.0")

# 2. 평가 실행
field_scores, field_methods, weighted_score, evaluation_table = evaluate_paca_performance(
    client_number,
    sp_construct,
    paca_construct
)

# 3. 결과 표시
st.metric("Overall Score", f"{weighted_score:.2f}")
st.dataframe(evaluation_table)
```

### 직접 사용 (Python)

```python
from evaluator import evaluate_constructs

field_scores, field_methods, weighted_score = evaluate_constructs(
    sp_construct, 
    paca_construct
)

print(f"Score: {weighted_score:.2f}")
```

## Construct 구조 요구사항

**중요:** SP와 PACA construct는 **같은 필드명을 가져야 합니다.**

### ✅ 권장하는 구조

```json
{
    "Chief complaint": "...",
    "Symptom name": "...",
    "Alleviating factor": "...",
    "Exacerbating factor": "...",
    "Triggering factor": "...",
    "Stressor": "...",
    "Diagnosis": "...",
    "Substance use": "...",
    "Current family structure": "...",
    "length": "8",
    "Suicidal ideation": "high|moderate|low",
    "Self mutilating behavior risk": "high|moderate|low",
    "Homicide risk": "high|moderate|low",
    "Suicidal plan": "presence|absence",
    "Suicidal attempt": "presence|absence",
    "Mood": "irritable|euphoric|elated|euthymic|dysphoric|depressed",
    "Verbal productivity": "increased|moderate|decreased",
    "Insight": "complete denial of illness|slight awareness...|awareness...|intellectual insight|true emotional insight",
    "Affect": "broad|restricted|blunt|...",
    "Perception": "Normal|Illusion|...",
    "Thought process": "Normal|Loosening...|...",
    "Thought content": "Normal|preoccupation|...",
    "Spontaneity": "(+)|(-)",
    "Social judgement": "Normal|Impaired",
    "Reliability": "Yes|No"
}
```

### ⚠️ 주의: 이전의 중첩 구조도 자동으로 처리됨

```json
// SP construct (중첩)
{
    "Chief complaint": "...",
    "Mental Status Examination": {
        "Mood": "depressed",
        "Affect": "blunt"
    },
    "Impulsivity": {
        "Suicidal ideation": "high"
    }
}

// PACA construct (평탄)
{
    "chief_complaint": "...",
    "mood": "dysphoric",
    "affect": "restricted",
    "suicidal_ideation": "moderate"
}

// 자동으로 일치시킴!
```

## 출력 형식

### 평가 테이블

| Field | Score | Method | Weight |
|-------|-------|--------|--------|
| Chief complaint | 0.85 | G-Eval | 1 |
| Mood | 1.00 | Behavior(\|Δ\|=0) | 2 |
| Suicidal ideation | 0.50 | Impulsivity(Δ=1) | 5 |
| ... | ... | ... | ... |

### 전체 점수

```
Overall Weighted Score: 0.87

Weighted_Score = (0.85×1 + 1.00×2 + 0.50×5 + ...) / (1 + 2 + 5 + ...)
               = ... / ...
               = 0.87
```

## 문제 해결

### "Field 'xxx' not in PSYCHE RUBRIC"

**원인:** Construct에 PSYCHE RUBRIC에 없는 필드가 있음

**해결:** 
1. Construct에서 불필요한 필드 제거
2. PSYCHE_RUBRIC에 필드 추가 (필요시)

### "Invalid values: SP=..., PACA=..."

**원인:** Behavior/Impulsivity 필드의 값이 정의된 후보가 아님

**해결:** Construct의 값을 확인하고 올바른 후보값으로 수정
```python
# Mood 필드의 유효한 값들
"irritable", "euphoric", "elated", "euthymic", "dysphoric", "depressed"
```

### "Missing value for field..."

**원인:** SP 또는 PACA construct에 필드가 없거나 값이 비어있음

**해결:** 두 construct 모두 필요한 필드를 채우기

## 성능 개선사항

| 항목 | 이전 | 현재 |
|------|------|------|
| 코드 줄 수 | 486 | ~300 |
| 함수 수 | 15+ | 10 |
| PSYCHE RUBRIC 정의 | Hardcoded in functions | Central dictionary |
| Construct 구조 호환성 | 낮음 (구조가 다르면 실패) | 높음 (자동 정규화) |
| 가독성 | 낮음 (복잡한 재귀) | 높음 (명확한 함수) |
| 유지보수 | 어려움 | 쉬움 |

## 향후 개선 사항

1. **Construct 자동 생성:** 평가 전에 construct를 표준 형식으로 자동 변환
2. **배치 평가:** 여러 클라이언트를 한 번에 평가
3. **평가 결과 저장:** Firebase에 평가 결과 자동 저장
4. **시각화:** 점수 분포, 가중치 분석 등의 차트
5. **상세 리포트:** PDF 형식의 종합 평가 리포트
