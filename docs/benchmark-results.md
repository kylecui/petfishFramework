# Pass^8 Benchmark Results

> Model: Qwen/Qwen2.5-72B-Instruct | k=8 | Date: 2026-07-05

## Task: What is 17 * 23? Use the calculator tool.

### petfishFramework
- exact_match: 8/8 ✅
- numeric_match: 8/8 ✅
- unique answers: 1

| Run # | Answer |
|---|---|
| 1 | 391 |
| 2 | 391 |
| 3 | 391 |
| 4 | 391 |
| 5 | 391 |
| 6 | 391 |
| 7 | 391 |
| 8 | 391 |

### Raw API (no framework)
- exact_match: 0/8 ❌
- numeric_match: 8/8 ✅
- unique answers: 6

| Run # | Answer |
|---|---|
| 1 | Sure, I can help with that. Using the calculator tool, 17 * 23 equals 391. |
| 2 | To calculate \( 17 \times 23 \):

\[ 17 \times 23 = 391 \]

So, the answer is 391. |
| 3 | Sure, I can help with that. Using a calculator, 17 * 23 equals 391. |
| 4 | Sure, I can help with that. Using the calculator tool, 17 * 23 equals 391. |
| 5 | Sure, I'll use the calculator tool to find the product of 17 and 23.

17 * 23 = 391

So, the answer is 391. |
| 6 | Sure, I can help with that. Using the calculator tool, 17 * 23 equals 391. |
| 7 | Sure, let's calculate that:

17 * 23 = 391

So, the product of 17 and 23 is 391. |
| 8 | Sure, I can help with that. Using the calculator, 17 * 23 equals 391. |

### Comparison
| Metric | petfishFramework | Raw API |
|---|---|---|
| exact_match | ✅ 8/8 | ❌ 0/8 |
| numeric_match | ✅ 8/8 | ✅ 8/8 |
| unique answers | 1 | 6 |

## Task: What is (45 + 55) / 2? Use the calculator tool.

### petfishFramework
- exact_match: 8/8 ✅
- numeric_match: 8/8 ✅
- unique answers: 1

| Run # | Answer |
|---|---|
| 1 | 50 |
| 2 | 50 |
| 3 | 50 |
| 4 | 50 |
| 5 | 50 |
| 6 | 50 |
| 7 | 50 |
| 8 | 50 |

### Raw API (no framework)
- exact_match: 0/8 ❌
- numeric_match: 8/8 ✅
- unique answers: 8

| Run # | Answer |
|---|---|
| 1 | Sure, I can help you calculate that. 

(45 + 55) / 2 = 100 / 2 = 50

So the result is 50. |
| 2 | Sure, I can help you with that calculation. 

(45 + 55) / 2 = 100 / 2 = 50

So the result is 50. |
| 3 | Sure, I can help you with that calculation. 

(45 + 55) / 2 = 100 / 2 = 50

So, the result is 50. |
| 4 | Sure, let's calculate that:

\[
\frac{45 + 55}{2} = \frac{100}{2} = 50
\]

So, the result is 50. |
| 5 | Sure, I can help you calculate that. However, I don't need to use a calculator for this simple arithmetic problem. The c |
| 6 | The calculation (45 + 55) / 2 is straightforward and doesn't necessarily require a calculator, but I can certainly help  |
| 7 | Sure, I can help with that calculation. However, I don't need a calculator to figure this out, but I'll proceed as if I' |
| 8 | Sure, let's calculate that:

(45 + 55) / 2 = 100 / 2 = 50

So, the result is 50. |

### Comparison
| Metric | petfishFramework | Raw API |
|---|---|---|
| exact_match | ✅ 8/8 | ❌ 0/8 |
| numeric_match | ✅ 8/8 | ✅ 8/8 |
| unique answers | 1 | 8 |

## Task: What is 2^10? Use the calculator tool.

### petfishFramework
- exact_match: 8/8 ✅
- numeric_match: 8/8 ✅
- unique answers: 1

| Run # | Answer |
|---|---|
| 1 | 1024 |
| 2 | 1024 |
| 3 | 1024 |
| 4 | 1024 |
| 5 | 1024 |
| 6 | 1024 |
| 7 | 1024 |
| 8 | 1024 |

### Raw API (no framework)
- exact_match: 0/8 ❌
- numeric_match: 8/8 ✅
- unique answers: 7

| Run # | Answer |
|---|---|
| 1 | Sure, I'll calculate that for you. \(2^{10}\) equals 1024. |
| 2 | Sure, let's calculate \(2^{10}\) using a calculator.

\[ 2^{10} = 1024 \]

So, \(2^{10}\) equals 1024. |
| 3 | Sure, I can calculate that for you. \(2^{10}\) equals 1024. |
| 4 | Sure, I can help with that. Using the calculator tool, \(2^{10}\) is:

\[ 2^{10} = 1024 \] |
| 5 | Sure, I can calculate that for you. \(2^{10}\) equals 1024. |
| 6 | Sure, let's calculate \(2^{10}\) using a calculator.

\(2^{10} = 1024\)

So, \(2^{10}\) equals 1024. |
| 7 | Sure, let's calculate \(2^{10}\).

Using a calculator, \(2^{10} = 1024\).

So, \(2^{10}\) is 1024. |
| 8 | Sure, I can help with that. Using a calculator, \(2^{10}\) is:

\[ 2^{10} = 1024 \] |

### Comparison
| Metric | petfishFramework | Raw API |
|---|---|---|
| exact_match | ✅ 8/8 | ❌ 0/8 |
| numeric_match | ✅ 8/8 | ✅ 8/8 |
| unique answers | 1 | 7 |

## Overall

| Task | PF exact | PF numeric | Raw exact | Raw numeric | PF unique | Raw unique |
|---|---|---|---|---|---|---|
| 17×23 | ✅ | ✅ | ❌ | ✅ | — | — |
