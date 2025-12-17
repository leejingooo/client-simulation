# 세션 상태 충돌 분석 보고서

## 분석 일시
2025-12-17

## 분석 범위
- 01_가상면담가에_대한_전문가_검증.py
- 02_가상환자에_대한_전문가_검증.py

## Streamlit 세션 격리 메커니즘

**중요**: Streamlit의 세션 상태는 **브라우저 세션별로 완전히 격리**됩니다.
- 각 브라우저/탭은 독립적인 세션을 가짐
- 다른 사용자가 다른 브라우저에서 접속 → 세션 충돌 없음
- 같은 사용자가 같은 브라우저에서 여러 탭 → 세션 공유 (의도된 동작)

## 현재 구조 분석

### 01_가상면담가에_대한_전문가_검증.py ✅

**세션 상태 구조:**
```python
st.session_state = {
    'validation_stage': 'intro',  # 전역
    'expert_name': 'kim_soo_min',  # 전역
    'expert_kim_soo_min': {  # 전문가별 격리
        'current_experiment_index': 0,
        'validation_responses': {},
        'firebase_loaded': False
    }
}
```

**평가:**
- ✅ 전문가별 상태 격리 (`expert_{expert_name}` 패턴)
- ✅ 같은 전문가가 여러 탭에서 작업해도 일관성 유지
- ✅ Firebase 키도 전문가별 분리 (`expert_{sanitized_name}_{client}_{exp}`)

### 02_가상환자에_대한_전문가_검증.py ⚠️

**세션 상태 구조:**
```python
st.session_state = {
    'sp_validation_stage': 'intro',  # 전역
    'current_sp_index': 0,  # 전역 (주의)
    'sp_validation_responses': {},  # 전역 (주의)
    'sp_validation_progress': {},  # 전역
    'expert_name': 'kim_soo_min',  # 전역
    'sp_progress_loaded': True,  # 전역 (주의)
    'sp_validation_kim_soo_min_1_6201': {  # SP별 격리
        'agent': ...,
        'memory': ...
    }
}
```

**평가:**
- ⚠️ 일부 상태가 전역으로 관리됨
- ✅ Firebase 키는 전문가별 분리 (`sp_validation_{sanitized_name}_{client}_{page}`)
- ⚠️ 같은 브라우저에서 여러 탭 사용 시 혼란 가능

## 충돌 가능성 평가

### 다른 전문가 간 충돌: ❌ 없음
- 각 전문가는 다른 브라우저/기기 사용
- Streamlit 세션이 완전히 격리됨
- Firebase 저장도 전문가명으로 분리됨

### 같은 전문가가 여러 탭 사용: ⚠️ 혼란 가능 (02번 페이지)
**01번 페이지:** 문제 없음 (전문가별 격리 구조)
**02번 페이지:** 
- `current_sp_index`가 전역 → 탭 간 공유됨
- 탭 A에서 가상환자 3 작업, 탭 B에서 가상환자 5 작업 시 인덱스 충돌

## 실제 위험도 평가

### 낮은 위험 (현재 사용 패턴)
1. **일반적 사용:** 전문가 1명 = 1개 탭
2. **Firebase 저장:** 각 SP별로 독립적 저장
3. **데이터 손실 없음:** 저장은 `{client}_{page}` 키로 분리

### 잠재적 문제 시나리오
1. 전문가가 실수로 2개 탭 열고 작업
2. 탭 A에서 가상환자 3, 탭 B에서 가상환자 5 선택
3. `current_sp_index` 충돌 → UI 혼란 (데이터는 안전)

## 권장사항

### 옵션 1: 현상 유지 (권장) ✅
**이유:**
- 실제 사용 패턴에서 문제 발생 확률 극히 낮음
- Streamlit 세션 격리가 충분히 안전함
- 데이터는 Firebase에 안전하게 저장됨
- 추가 복잡도 불필요

**조치:**
- 코드에 주석 추가하여 세션 격리 명확히 설명

### 옵션 2: 02번 페이지 구조 개선 (선택)
01번 페이지처럼 전문가별 상태 격리:
```python
st.session_state[f'sp_expert_{expert_name}'] = {
    'current_sp_index': 0,
    'validation_responses': {},
    'progress_loaded': False
}
```

**장점:**
- 01번과 일관된 구조
- 여러 탭 사용 시 더 명확

**단점:**
- 불필요한 복잡도 증가
- 리팩토링 범위 큼
- 실제 이점 미미

## 결론

**현재 구조는 안전합니다.**

1. ✅ 다른 전문가 간 충돌 없음 (Streamlit 세션 격리)
2. ✅ Firebase 저장은 전문가별로 완전히 분리
3. ⚠️ 같은 전문가가 여러 탭 사용 시 UI 혼란 가능 (데이터는 안전)
4. ✅ 실제 사용 패턴에서는 문제 없음

**권장 조치:**
- 현상 유지 + 주석 추가로 명확성 확보
- 필요시 사용자에게 "한 번에 한 탭만 사용" 안내
