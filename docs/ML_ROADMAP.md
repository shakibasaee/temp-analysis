# Machine learning roadmap

This plan adapts the end-to-end project workflow in [chapter 2 of *Hands-On Machine Learning*, third edition](https://www.oreilly.com/library/view/hands-on-machine-learning/9781098125967/ch02.html): define the prediction task, check assumptions and data rights, reserve future observations for evaluation, fit preprocessing on training data, analyze errors, then monitor the system. The [author's companion notebooks](https://github.com/ageron/handson-ml3) are a learning reference, not code or data copied into this repository. Random cross-validation from a general tabular example is inappropriate here; forecasts are evaluated in date order.

| Reading path | Practice in this repository |
|---|---|
| [Chapter 2: end-to-end project](https://www.oreilly.com/library/view/hands-on-machine-learning/9781098125967/ch02.html) | Run the benchmark, inspect the new error report, and document data assumptions before changing a model. Use chronological folds instead of random splits. |
| [Chapter 4: training models](https://www.oreilly.com/library/view/hands-on-machine-learning/9781098125967/ch04.html) | Compare the existing calendar regression and Ridge pipeline with persistence; review why a small numeric gain is insufficient. |
| [Chapter 7: ensembles](https://www.oreilly.com/library/view/hands-on-machine-learning/9781098125967/ch07.html) | Treat the existing Extra Trees model as a comparator. Revisit it only after later data and the simpler baselines are trustworthy. |

## Current baseline

The task is a one-day-ahead estimate of each city's recorded temperature after today's observation. The bundled five-city CSV ends on 2024-12-31. Its provider, temperature definition, timezone, and reuse license are unknown. On the July–December 2024 holdout (920 targets), persistence has MAE 1.1568 C, seven-day seasonal naive 2.6522 C, and the existing calendar linear regression 2.9943 C. Ridge's 1.1490 C test MAE does not justify changing the selected policy because its validation gain is below the configured 2% threshold. These are internal benchmark values, not evidence of current forecasting skill.

The project owner's intended product is broader: a user-selected date 1–30 days ahead with daily mean, minimum, and maximum temperature, evaluated by MAE and the percentage within ±2 C. This has not been implemented or validated. The [Week 1 execution plan](WEEK1_PLAN.md) and [draft product contract](PRODUCT_CONTRACT.md) establish the data and evaluation gates before expanding the forecast horizon.

The new diagnostic report shows persistence MAE rising from 0.9097 C in July to 1.4142 C in December 2024; median absolute error is 0.8 C and the 90th percentile is 2.4 C. Two of the largest errors occur on 2024-12-15 in Mashhad (12.3 C) and Yazd (10.7 C). This is a prompt to verify the source records and investigate cold-season performance, not evidence that the model or data is wrong. Do not use these holdout observations to tune a replacement model.

## Short term: next 2–6 weeks

| Goal | Completion evidence |
|---|---|
| Document the data contract and rights | Record provider, station/location IDs, retrieval date, timezone, daily temperature definition, cleaning steps, and redistribution permission. Until then, label the bundled data unverified and use the synthetic generator for demonstrations. |
| Diagnose selected-model failures (implemented in this branch) | Benchmark JSON reports held-out MAE by month and city, median and 90th-percentile absolute error, and five largest errors. Dashboard shows the monthly city table. Tests verify row alignment and totals. This analysis is performed after selection and must not be used to retune the 2024 holdout. |
| Acquire a genuinely later evaluation period | Add at least 12 consecutive months after 2024 for the same locations, with authorized and explicitly defined daily mean/minimum/maximum values. Validate gaps and units before scoring. If unavailable, publish no new real-world accuracy claim. |
| Re-evaluate the baseline | Define issue-date-safe baselines for each supported horizon and target. Report chronological rolling-fold and untouched later-period MAE and within-±2 C rate by horizon, target, city, and month, with dates and counts. Keep all preprocessing fitted within each training fold. |

## Long term: following 2–6 months

| Goal | Completion evidence |
|---|---|
| Reliable observation pipeline | Ingest an authorized source with source metadata, schema checks, duplicate/gap checks, and freshness monitoring. Target at least 99% complete daily city records and alert when the latest observation is more than 48 hours old. |
| Champion–challenger model policy | Set acceptance thresholds before testing, then consider a new model only after multiple later rolling origins show a meaningful gain over an issue-date-safe baseline without hiding poor cities, targets, or horizons in a pooled average. Evaluate once on a newly reserved future test period. |
| Honest uncertainty | Calibrate 80% and 90% prediction intervals on past residuals, then measure coverage and interval width on later dates by city, target, and horizon. Do not show intervals until coverage is reported. |
| Product expansion | Add upload, export, or live-weather integration only when its input contract, provenance, failure behavior, and end-to-end tests are defined. Keep the dashboard's stale-data warning. |
| Public review readiness | Document code and data licenses, keep CI green, remove or archive the unrelated large CSV by team decision, and ensure README claims match the app before pinning the repository. |

The proposed completeness, freshness, and coverage thresholds are project targets, not measured results or claims from the book. Multi-horizon acceptance thresholds must be set in the product contract before later test results are examined. Deep learning is deliberately deferred: the current data spans only two years and the simple baseline is difficult to beat reliably.
