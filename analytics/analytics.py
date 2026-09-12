"""
analytics.py
------------
Implements Units 2 (Descriptive Analytics), 3 (Probability) and
4 (Sampling & Estimation) of the syllabus on the student dataset,
and exports everything the web dashboard needs as output.json.

Run:  python3 analytics/analytics.py
"""

import json
import math
import os
import random
import pandas as pd
import numpy as np
from scipy import stats

random.seed(7)
np.random.seed(7)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
CSV_PATH = os.path.join(PROJECT_ROOT, "data", "students.csv")
OUT_PATH = os.path.join(PROJECT_ROOT, "web", "output.json")

SUBJECTS = ["DS", "DBMS", "OS", "MATH", "ENG"]
SEMESTERS = [1, 2, 3, 4]
PASS_MARK = 40


# ---------------------------------------------------------------------
# 1. Load + identify data types (Unit 2: Data Types and Scales)
# ---------------------------------------------------------------------
def load_data():
    df = pd.read_csv(CSV_PATH)
    mark_cols = [f"sem{s}_{sub}" for s in SEMESTERS for sub in SUBJECTS]
    for c in mark_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df, mark_cols


def classify_data_types(df, mark_cols):
    """Unit 2: nominal / ordinal / interval / ratio classification."""
    return {
        "enrollment_no": "Nominal (identifier)",
        "name": "Nominal (categorical, non-numeric)",
        "gender": "Nominal (categorical, binary)",
        "mobile": "Nominal (identifier)",
        "city": "Nominal (categorical)",
        "marks (all subjects)": "Ratio (numeric, true zero, semester-wise, e.g. " +
                                 f"{mark_cols[0]})",
    }


# ---------------------------------------------------------------------
# 2. Missing value treatment (Practical 3)
# ---------------------------------------------------------------------
def treat_missing_values(df, mark_cols):
    report = {"gender_missing_before": int(df["gender"].isna().sum()
                                            | (df["gender"] == "")
                                            .sum() if False else df["gender"].isna().sum())}
    # Gender: mode imputation
    if df["gender"].isna().sum() > 0:
        mode_gender = df["gender"].mode(dropna=True)[0]
        df["gender"] = df["gender"].fillna(mode_gender)

    # Marks: mean imputation, computed per subject-semester column
    marks_missing_before = int(df[mark_cols].isna().sum().sum())
    for c in mark_cols:
        df[c] = df[c].fillna(round(df[c].mean(), 1))
    marks_missing_after = int(df[mark_cols].isna().sum().sum())

    report.update({
        "marks_missing_before": marks_missing_before,
        "marks_missing_after": marks_missing_after,
        "method": "Gender -> mode imputation; Marks -> column-wise mean imputation",
    })
    return df, report


# ---------------------------------------------------------------------
# 3. Descriptive statistics (Unit 2)
# ---------------------------------------------------------------------
def descriptive_stats(df):
    """Per subject, per semester: mean, median, quartiles, variance,
    std dev, skewness, kurtosis, and variation (max-min)."""
    results = {}
    for sem in SEMESTERS:
        sem_key = f"sem{sem}"
        results[sem_key] = {}
        for sub in SUBJECTS:
            col = f"sem{sem}_{sub}"
            series = df[col].dropna()
            q1, med, q3 = np.percentile(series, [25, 50, 75])
            results[sem_key][sub] = {
                "mean": round(series.mean(), 2),
                "median": round(med, 2),
                "q1": round(q1, 2),
                "q3": round(q3, 2),
                "decile_9": round(np.percentile(series, 90), 2),
                "variance": round(series.var(ddof=1), 2),
                "std_dev": round(series.std(ddof=1), 2),
                "skewness": round(stats.skew(series), 3),
                "kurtosis": round(stats.kurtosis(series), 3),
                "max_minus_min": round(series.max() - series.min(), 2),
                "min": round(series.min(), 2),
                "max": round(series.max(), 2),
            }
    return results


def semester_averages(df):
    """Average overall marks per semester -> used for the trend chart."""
    out = []
    for sem in SEMESTERS:
        cols = [f"sem{sem}_{sub}" for sub in SUBJECTS]
        out.append(round(df[cols].mean(axis=1).mean(), 2))
    return out


def gender_distribution(df):
    counts = df["gender"].value_counts().to_dict()
    return {"Male": int(counts.get("M", 0)), "Female": int(counts.get("F", 0))}


def city_distribution(df):
    return df["city"].value_counts().to_dict()


# ---------------------------------------------------------------------
# 4. Probability (Unit 3)
# ---------------------------------------------------------------------
def probability_analysis(df, mark_cols):
    # Overall pass probability per subject (any semester), PMF-style
    pass_probs = {}
    for sub in SUBJECTS:
        cols = [f"sem{s}_{sub}" for s in SEMESTERS]
        all_marks = pd.concat([df[c] for c in cols])
        pass_probs[sub] = round((all_marks >= PASS_MARK).mean(), 3)

    # Binomial model: P(a student passes exactly k of 5 sem1 subjects)
    sem1_cols = [f"sem1_{sub}" for sub in SUBJECTS]
    pass_counts = (df[sem1_cols] >= PASS_MARK).sum(axis=1)
    p_hat = (df[sem1_cols] >= PASS_MARK).values.mean()
    n = len(SUBJECTS)
    binomial_pmf = {
        str(k): round(stats.binom.pmf(k, n, p_hat), 4) for k in range(n + 1)
    }

    # Bayes' theorem: P(overall pass | city = Vapi) vs P(overall pass)
    df["sem1_overall_pass"] = (df[sem1_cols] >= PASS_MARK).all(axis=1)
    p_pass = df["sem1_overall_pass"].mean()
    vapi = df[df["city"] == "Vapi"]
    p_pass_given_vapi = vapi["sem1_overall_pass"].mean() if len(vapi) else 0
    p_vapi = len(vapi) / len(df)
    p_vapi_given_pass = (
        (p_pass_given_vapi * p_vapi) / p_pass if p_pass > 0 else 0
    )

    # Normal fit over sem1 overall average marks (for PDF/CDF illustration)
    overall_sem1 = df[sem1_cols].mean(axis=1)
    mu, sigma = overall_sem1.mean(), overall_sem1.std(ddof=1)

    return {
        "pass_probability_per_subject": pass_probs,
        "binomial": {
            "n_subjects": n,
            "p_pass_single_subject": round(p_hat, 3),
            "pmf_k_subjects_passed": binomial_pmf,
        },
        "bayes_theorem": {
            "P(pass_all_sem1)": round(p_pass, 3),
            "P(city=Vapi)": round(p_vapi, 3),
            "P(pass_all_sem1 | city=Vapi)": round(p_pass_given_vapi, 3),
            "P(city=Vapi | pass_all_sem1) [via Bayes]": round(p_vapi_given_pass, 3),
        },
        "normal_fit_sem1_average": {"mean": round(mu, 2), "std_dev": round(sigma, 2)},
    }


# ---------------------------------------------------------------------
# 5. Sampling & Estimation (Unit 4)
# ---------------------------------------------------------------------
def sampling_and_estimation(df):
    population = df[[f"sem1_{sub}" for sub in SUBJECTS]].mean(axis=1).values
    pop_mean = population.mean()
    pop_std = population.std(ddof=0)

    # Central Limit Theorem demo: draw many samples, record sample means
    sample_size = 15
    n_samples = 500
    sample_means = [
        np.random.choice(population, size=sample_size, replace=True).mean()
        for _ in range(n_samples)
    ]
    clt_mean_of_means = round(float(np.mean(sample_means)), 2)
    clt_std_of_means = round(float(np.std(sample_means, ddof=1)), 3)
    predicted_se = round(pop_std / math.sqrt(sample_size), 3)  # CLT prediction

    # Histogram bins of the sample-mean distribution for the frontend
    hist, edges = np.histogram(sample_means, bins=12)
    clt_histogram = {
        "bins": [round(e, 1) for e in edges[:-1]],
        "counts": hist.tolist(),
    }

    # Single-sample point estimate of population mean (Method of Moments == sample mean for a Normal)
    one_sample = np.random.choice(population, size=sample_size, replace=False)
    mom_estimate_mean = round(float(one_sample.mean()), 2)
    mom_estimate_var = round(float(one_sample.var(ddof=1)), 2)

    # MLE for Normal distribution: mu_hat = sample mean, sigma_hat^2 = biased variance
    mle_mu = round(float(one_sample.mean()), 2)
    mle_sigma2 = round(float(one_sample.var(ddof=0)), 2)

    # Required sample size for +-3 marks margin of error at 95% confidence
    z_95 = 1.96
    margin_of_error = 3
    required_n = math.ceil((z_95 * pop_std / margin_of_error) ** 2)

    return {
        "population_mean": round(float(pop_mean), 2),
        "population_std_dev": round(float(pop_std), 2),
        "clt_demo": {
            "sample_size": sample_size,
            "n_samples_drawn": n_samples,
            "mean_of_sample_means": clt_mean_of_means,
            "std_dev_of_sample_means": clt_std_of_means,
            "predicted_std_error_from_clt": predicted_se,
            "histogram": clt_histogram,
        },
        "method_of_moments_estimate": {
            "sample_size": sample_size,
            "estimated_mean": mom_estimate_mean,
            "estimated_variance": mom_estimate_var,
        },
        "mle_estimate": {
            "estimated_mu": mle_mu,
            "estimated_sigma_squared": mle_sigma2,
        },
        "required_sample_size_95pct_ci_pm3marks": int(required_n),
    }


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------
def main():
    df, mark_cols = load_data()
    data_types = classify_data_types(df, mark_cols)
    df, missing_report = treat_missing_values(df, mark_cols)

    output = {
        "meta": {
            "n_students": len(df),
            "subjects": SUBJECTS,
            "semesters": SEMESTERS,
            "pass_mark": PASS_MARK,
        },
        "data_types": data_types,
        "missing_value_treatment": missing_report,
        "descriptive_stats": descriptive_stats(df),
        "semester_averages": semester_averages(df),
        "gender_distribution": gender_distribution(df),
        "city_distribution": city_distribution(df),
        "probability": probability_analysis(df, mark_cols),
        "sampling_estimation": sampling_and_estimation(df),
        "students_table": df[["enrollment_no", "name", "gender", "city"]
                              + [f"sem{s}_{sub}" for s in SEMESTERS for sub in SUBJECTS]]
        .head(20).to_dict(orient="records"),
    }

    with open(OUT_PATH, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Analytics complete. Wrote results to {OUT_PATH}")
    print(f"Students: {len(df)} | Missing marks fixed: {missing_report['marks_missing_before']}")


if __name__ == "__main__":
    main()
