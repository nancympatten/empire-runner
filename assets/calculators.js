"use strict";

(() => {
  const read = (root, id) => {
    const el = root.querySelector('[data-field="' + id + '"]');
    if (!el || el.value.trim() === "") return NaN;
    return Number(el.value);
  };
  const money = (n, currency) =>
    currency + " " + n.toLocaleString(undefined, {maximumFractionDigits: 2});
  const pct = (n) => Number.isFinite(n) ? n.toFixed(2) + "%" : "Not available";
  const number = (n) => Number.isFinite(n) ? n.toFixed(2) : "Not available";

  function calculate(mode, v) {
    const {
      price:p, rent:r, vacancy:vac, expenses:e, costs:c,
      down:d, rate:rate, years:y, maintenance:maint,
      management:mgmt, insurance:ins, tax, capex,
      extra:extra, growth:growth, horizon:horizon,
      salePrice:sale, saleCost:saleCost, renovation:reno,
      furnishedRent:furnishedRent, shortRent:shortRent,
      longRent:longRent, nights:nights, occupancy:occupancy,
      furnishingCost:furnishingCost, stressRent:stressRent,
      stressVacancy:stressVacancy, stressExpenses:stressExpenses,
      feeRate:feeRate, fixedFees:fixedFees
    } = v;

    const validPrice = p > 0;
    const annualRent = r * 12;
    const effectiveRent = annualRent * (1 - vac / 100);
    const operatingCosts = e + maint + ins + tax + capex;
    const noi = effectiveRent - operatingCosts;
    const loan = validPrice ? p * (1 - d / 100) : NaN;
    const monthlyRate = rate / 1200;
    const months = y * 12;
    const payment = monthlyRate === 0
      ? loan / months
      : loan * monthlyRate / (1 - Math.pow(1 + monthlyRate, -months));
    const annualDebt = payment * 12;
    const invested = p * d / 100 + c;
    const cashFlow = noi - annualDebt;

    const out = [];
    const add = (label, value) => out.push([label, value]);
    const addMoney = (label, value) => add(label, money(value, v.currency));

    switch (mode) {
      case "gross-rental-yield":
        if (!validPrice) break;
        addMoney("Annual scheduled rent", annualRent);
        add("Gross rental yield", pct(annualRent / p * 100));
        break;

      case "vacancy-adjusted-yield":
        if (!validPrice) break;
        addMoney("Annual rent after vacancy allowance", effectiveRent);
        add("Vacancy-adjusted yield", pct(effectiveRent / p * 100));
        break;

      case "net-rental-yield":
      case "capitalization-rate":
        if (!validPrice) break;
        addMoney("Effective annual rent", effectiveRent);
        addMoney("Operating expenses entered", operatingCosts);
        addMoney("Net operating income", noi);
        add("Net yield on acquisition cost", pct(noi / (p + c) * 100));
        if (mode === "capitalization-rate") {
          add("Cap rate on property price", pct(noi / p * 100));
        }
        break;

      case "net-operating-income":
        addMoney("Effective annual rent", effectiveRent);
        addMoney("Operating expenses", operatingCosts);
        addMoney("Annual NOI", noi);
        break;

      case "annual-cash-flow":
      case "cash-on-cash-return":
      case "dscr-analysis":
        if (!validPrice || !Number.isFinite(payment)) break;
        addMoney("Annual NOI", noi);
        addMoney("Annual debt service", annualDebt);
        addMoney("Annual pre-tax cash flow", cashFlow);
        if (mode === "cash-on-cash-return") {
          addMoney("Initial cash invested (price deposit + acquisition costs)", invested);
          add("Cash-on-cash return", invested > 0 ? pct(cashFlow / invested * 100) : "Not available");
        }
        if (mode === "dscr-analysis") {
          add("Debt service coverage ratio", annualDebt > 0 ? number(noi / annualDebt) + "x" : "No debt service");
        }
        break;

      case "mortgage-debt-service":
        if (!validPrice || !(y > 0)) break;
        addMoney("Estimated loan principal", loan);
        addMoney("Monthly principal-and-interest payment", payment);
        addMoney("Annual debt service", annualDebt);
        addMoney("Total scheduled payments over loan term", payment * months);
        break;

      case "break-even-occupancy": {
        const debtIncluded = Number.isFinite(annualDebt) ? annualDebt : 0;
        const fixedCosts = operatingCosts + debtIncluded;
        addMoney("Annual scheduled rent at 100% occupancy", annualRent);
        addMoney("Annual operating costs entered", operatingCosts);
        addMoney("Annual debt service included", debtIncluded);
        addMoney("Total annual costs to cover", fixedCosts);
        add("Break-even occupancy", annualRent > 0 ? pct(fixedCosts / annualRent * 100) : "Not available");
        add("Feasibility", fixedCosts / (annualRent || 1) > 1 ? "Required occupancy exceeds 100%; assumptions do not break even." : "Compare required occupancy with a defensible property-specific assumption.");
        break;
      }

      case "vacancy-sensitivity": {
        if (!validPrice) break;
        for (const assumption of [0, 5, 10, 15, 20, 30]) {
          const income = annualRent * (1 - assumption / 100);
          add("Vacancy " + assumption + "% — annual NOI", money(income - operatingCosts, v.currency));
        }
        break;
      }

      case "expense-ratio":
        add("Operating expense ratio", effectiveRent > 0 ? pct(operatingCosts / effectiveRent * 100) : "Not available");
        addMoney("Effective annual rent", effectiveRent);
        addMoney("Entered operating expenses", operatingCosts);
        break;

      case "acquisition-costs":
        addMoney("Purchase price", p);
        addMoney("Acquisition and closing costs", c);
        addMoney("Total project cost before financing", p + c + extra);
        addMoney("Additional initial works / fees", extra);
        break;

      case "down-payment-leverage":
        if (!validPrice) break;
        addMoney("Estimated loan", loan);
        addMoney("Down payment", p * d / 100);
        add("Loan-to-value ratio", pct(100 - d));
        addMoney("Cash required including acquisition costs", p * d / 100 + c);
        break;

      case "interest-rate-sensitivity":
        if (!validPrice || !(y > 0)) break;
        for (const assumption of [rate - 2, rate - 1, rate, rate + 1, rate + 2]) {
          if (assumption < 0) continue;
          const m = assumption / 1200;
          const pay = m === 0 ? loan / months : loan * m / (1 - Math.pow(1 + m, -months));
          add("Interest " + assumption.toFixed(2) + "% — monthly payment", money(pay, v.currency));
        }
        break;

      case "rent-escalation":
        if (r < 0 || growth <= -100 || !(horizon >= 0)) break;
        addMoney("Current monthly rent", r);
        addMoney("Monthly rent after " + horizon + " years", r * Math.pow(1 + growth / 100, horizon));
        addMoney("Annual rent after " + horizon + " years", r * 12 * Math.pow(1 + growth / 100, horizon));
        break;

      case "capital-expenditure":
        addMoney("Annual maintenance entered", maint);
        addMoney("Annual capital reserve entered", capex);
        addMoney("Combined annual maintenance and reserve", maint + capex);
        add("Reserve as share of effective rent", effectiveRent > 0 ? pct((maint + capex) / effectiveRent * 100) : "Not available");
        break;

      case "management-fees": {
        const fee = effectiveRent * feeRate / 100 + fixedFees;
        addMoney("Percentage-based management fee", effectiveRent * feeRate / 100);
        addMoney("Fixed management charges", fixedFees);
        addMoney("Total annual management fees", fee);
        addMoney("Effective rent after management fees", effectiveRent - fee);
        break;
      }

      case "insurance-property-tax":
        addMoney("Annual insurance", ins);
        addMoney("Annual property tax entered by user", tax);
        addMoney("Combined insurance and property tax", ins + tax);
        add("Share of effective rent", effectiveRent > 0 ? pct((ins + tax) / effectiveRent * 100) : "Not available");
        break;

      case "short-vs-long-term": {
        const shortIncome = shortRent * nights * occupancy / 100;
        const longIncome = longRent * 12 * (1 - vac / 100);
        addMoney("Short-term gross scenario revenue", shortIncome);
        addMoney("Long-term effective annual rent", longIncome);
        addMoney("Short-term less entered annual expenses", shortIncome - e);
        addMoney("Long-term less entered annual expenses", longIncome - e);
        add("Comparison assumption", "The same annual expense amount is applied to both scenarios; separate operating-cost assumptions are not modeled.");
        break;
      }

      case "furnished-vs-unfurnished": {
        const grossUplift = (furnishedRent - r) * 12 * (1 - vac / 100);
        const netUplift = grossUplift - extra;
        addMoney("Annual rent uplift after vacancy", grossUplift);
        addMoney("Additional annual furnishing operating costs", extra);
        addMoney("Annual incremental net income", netUplift);
        addMoney("Furnishing investment", furnishingCost);
        add("Simple payback period", netUplift > 0 ? number(furnishingCost / netUplift) + " years" : "Not available: incremental net income must be positive.");
        break;
      }

      case "renovation-payback": {
        addMoney("One-time renovation investment", reno);
        addMoney("Annual incremental net income after added costs", extra);
        add("Simple payback period", extra > 0 ? number(reno / extra) + " years" : "Not available: annual incremental net income must be positive.");
        add("Limitation", "Simple payback excludes discounting, financing, tax, future repairs and changes in resale value.");
        break;
      }

      case "hold-period-cash-flow":
        if (!Number.isFinite(annualDebt)) break;
        addMoney("Annual pre-tax cash flow", cashFlow);
        addMoney("Cumulative simple cash flow over " + horizon + " years", cashFlow * horizon);
        addMoney("Initial cash invested", invested);
        addMoney("Cumulative cash flow less initial cash invested", cashFlow * horizon - invested);
        add("Limitation", "Simple cumulative cash flow only; excludes sale proceeds, loan amortization changes, taxes and discounting.");
        break;

      case "exit-sale-scenario": {
        const selling = sale * saleCost / 100;
        addMoney("Assumed sale price", sale);
        addMoney("Selling costs", selling);
        addMoney("Estimated sale proceeds before debt payoff", sale - selling);
        addMoney("Estimated proceeds after entered loan balance", sale - selling - extra);
        add("Limitation", "The entered deduction combines outstanding loan balance and any other liabilities; excludes taxes and other unentered sale adjustments.");
        break;
      }

      case "investment-risk-stress-test": {
        const stressedIncome = annualRent * (1 - stressVacancy / 100);
        const stressedNOI = stressedIncome - stressExpenses;
        addMoney("Baseline NOI", noi);
        addMoney("Stressed annual rent after vacancy", stressedIncome);
        addMoney("Total stressed annual operating expenses", stressExpenses);
        addMoney("Stressed NOI", stressedNOI);
        addMoney("Change in NOI under stress", stressedNOI - noi);
        add("Stress-case vacancy assumption", pct(stressVacancy));
        add("Limitation", "Stress vacancy replaces the baseline vacancy assumption; it is not added to it.");
        break;
      }

      default:
        add("Status", "Unknown calculator mode.");
    }

    return out;
  }

  function start() {
    document.querySelectorAll("[data-rental-calculator]").forEach((root) => {
      if (root.dataset.initialized === "yes") return;
      root.dataset.initialized = "yes";
      const mode = root.dataset.mode;
      const currencyInput = root.querySelector("[data-currency]");
      const result = root.querySelector("[data-results]");
      const button = root.querySelector("[data-calculate]");
      button.addEventListener("click", () => {
        const currency = (currencyInput.value || "").replace(/[^A-Za-z0-9 ._-]/g, "").slice(0, 12) || "Currency";
        const ids = ["price","rent","vacancy","expenses","costs","down","rate","years","maintenance","management","insurance","tax","capex","extra","growth","horizon","salePrice","saleCost","renovation","furnishedRent","shortRent","longRent","nights","occupancy","furnishingCost","stressVacancy","stressExpenses","feeRate","fixedFees"];
        const required = (root.dataset.required || "").split(",").filter(Boolean);
        const v = {currency};
        ids.forEach((id) => { v[id] = 0; });
        required.forEach((id) => { v[id] = read(root, id); });
        const errors = [];
        required.forEach((id) => {
          if (!Number.isFinite(v[id])) errors.push("Enter a valid value for " + id + ".");
          else if (v[id] < 0 && id !== "growth") errors.push(id + " cannot be negative.");
        });
        if (required.includes("price") && v.price <= 0) errors.push("Purchase price must be greater than zero.");
        ["vacancy","down","occupancy","saleCost","stressVacancy","feeRate"].forEach((id) => {
          if (required.includes(id) && (v[id] < 0 || v[id] > 100)) errors.push(id + " must be between 0 and 100%.");
        });
        if (required.includes("rate") && (v.rate < 0 || v.rate > 100)) errors.push("Interest rate must be between 0 and 100%.");
        if (required.includes("years") && (v.years < 1 || v.years > 50)) errors.push("Loan term must be between 1 and 50 years.");
        if (required.includes("growth") && v.growth <= -100) errors.push("Annual rent change must be greater than -100%.");
        if (required.includes("horizon") && (v.horizon < 0 || v.horizon > 100)) errors.push("Analysis period must be between 0 and 100 years.");
        ["years","nights","horizon"].forEach((id) => {
          if (required.includes(id) && !Number.isInteger(v[id])) errors.push(id + " must be a whole number.");
        });
        if (required.includes("salePrice") && v.salePrice <= 0) errors.push("Assumed sale price must be greater than zero.");
        if (required.includes("nights") && (v.nights <= 0 || v.nights > 366)) errors.push("Rental nights must be between 1 and 366.");
        if (errors.length) {
          result.textContent = errors.join(" ");
          return;
        }
        const rows = calculate(mode, v);
        if (!rows.length || rows.some((row) => row.some((value) => value === undefined))) {
          result.textContent = "Unable to calculate this scenario. Check the required assumptions.";
          return;
        }
        result.replaceChildren();
        const heading = document.createElement("h3");
        heading.textContent = "Illustrative results";
        const list = document.createElement("ul");
        rows.forEach(([label, value]) => {
          const item = document.createElement("li");
          const strong = document.createElement("strong");
          strong.textContent = label + ": ";
          item.append(strong, document.createTextNode(String(value)));
          list.append(item);
        });
        const note = document.createElement("p");
        note.className = "small";
        note.textContent = "Scenario only, not a forecast or advice. Results depend on the inputs supplied. Verify financing, taxes, legal requirements, operating costs and sale assumptions independently. Some modes use simplified assumptions and exclude costs not entered.";
        result.append(heading, list, note);
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, {once:true});
  } else {
    start();
  }
})();
