# Pass^8 Benchmark Results

> Model: Qwen/Qwen2.5-72B-Instruct | k=8 | Date: 2026-07-05

## Task: What is 17 * 23? Use the calculator tool.

### petfishFramework
- exact_match: 0/8 ❌
- numeric_match: 0/8 ❌
- unique answers: 2

| Run # | Answer |
|---|---|
| 1 | 391.0 |
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
| 1 | To calculate 17 * 23, you can use a calculator or do it manually. However, since you asked to use the calculator tool, l |
| 2 | Sure, using the calculator tool, 17 * 23 equals 391. |
| 3 | Sure, let's calculate that:

17 * 23 = 391

So, the answer is 391. |
| 4 | Sure, I can help with that. Using the calculator tool, 17 * 23 equals 391. |
| 5 | Sure, I can help with that. 17 * 23 equals 391. |
| 6 | Sure, I can help with that. Using the calculator, 17 * 23 equals 391. |
| 7 | Sure, I can help with that. Using the calculator, 17 * 23 equals 391. |
| 8 | Sure, I can help with that. Using the calculator, 17 * 23 equals 391. |

### Comparison
| Metric | petfishFramework | Raw API |
|---|---|---|
| exact_match | ❌ 0/8 | ❌ 0/8 |
| numeric_match | ❌ 0/8 | ✅ 8/8 |
| unique answers | 2 | 6 |

## Task: What is (45 + 55) / 2? Use the calculator tool.

### petfishFramework
- exact_match: 8/8 ✅
- numeric_match: 8/8 ✅
- unique answers: 1

| Run # | Answer |
|---|---|
| 1 | 50.0 |
| 2 | 50.0 |
| 3 | 50.0 |
| 4 | 50.0 |
| 5 | 50.0 |
| 6 | 50.0 |
| 7 | 50.0 |
| 8 | 50.0 |

### Raw API (no framework)
- exact_match: 0/8 ❌
- numeric_match: 8/8 ✅
- unique answers: 6

| Run # | Answer |
|---|---|
| 1 | Sure, let's calculate that:

\[
(45 + 55) / 2 = 100 / 2 = 50
\]

So, the result is 50. |
| 2 | Sure, let's use the calculator to solve this:

\[
\frac{45 + 55}{2} = \frac{100}{2} = 50
\]

The result is 50. |
| 3 | Sure, I can help you calculate that. However, I don't need to use a calculator for this simple arithmetic problem. The c |
| 4 | Sure, let's calculate that:

\[
\frac{45 + 55}{2} = \frac{100}{2} = 50
\]

So, the answer is 50. |
| 5 | Sure, let's calculate that:

\[
\frac{45 + 55}{2} = \frac{100}{2} = 50
\]

So, the answer is 50. |
| 6 | Sure, I can help you calculate that. 

(45 + 55) / 2 = 100 / 2 = 50

So, the result is 50. |
| 7 | Sure, I can help you calculate that. However, I don't need to use a calculator for this simple arithmetic problem. The c |
| 8 | Sure, I can help you calculate that. 

(45 + 55) / 2 = 100 / 2 = 50

So, the result is 50. |

### Comparison
| Metric | petfishFramework | Raw API |
|---|---|---|
| exact_match | ✅ 8/8 | ❌ 0/8 |
| numeric_match | ✅ 8/8 | ✅ 8/8 |
| unique answers | 1 | 6 |

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
- numeric_match: 0/8 ❌
- unique answers: 8

| Run # | Answer |
|---|---|
| 1 | Sure, using the calculator tool, \(2^{10}\) is equal to 1024. |
| 2 | Sure, I can calculate that for you. \(2^{10}\) is equal to 1024. |
| 3 | Sure, I can help with that calculation. \(2^{10}\) equals 1024. |
| 4 | Sure, let's calculate \(2^{10}\):

\[ 2^{10} = 1024 \]

So, \(2^{10}\) is 1024. |
| 5 | Sure, using the calculator tool, \(2^{10} = 1024\). |
| 6 | Sure, let's calculate \(2^{10}\).

Using a calculator, \(2^{10} = 1024\). |
| 7 | Sure, let's calculate \(2^{10}\) using the calculator.

\[ 2^{10} = 1024 \]

So, \(2^{10}\) equals 1024. |
| 8 | Sure, let's calculate \(2^{10}\):

\[ 2^{10} = 1024 \]

So, \(2^{10}\) equals 1024. |

### Comparison
| Metric | petfishFramework | Raw API |
|---|---|---|
| exact_match | ✅ 8/8 | ❌ 0/8 |
| numeric_match | ✅ 8/8 | ❌ 0/8 |
| unique answers | 1 | 8 |

## Overall

| Task | PF exact | PF numeric | Raw exact | Raw numeric | PF unique | Raw unique |
|---|---|---|---|---|---|---|
| 17×23 | ✅ | ✅ | ❌ | ❌ | — | — |
