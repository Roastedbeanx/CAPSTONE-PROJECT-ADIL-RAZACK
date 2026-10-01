
#  **Data Governance Document — Presight Data Pipeline**

***

##  **Section 1 — Data Inventory**

| Dataset                    | Source system             | Format | Update frequency | Volume estimate  | Daily growth |
| -------------------------- | ------------------------- | ------ | ---------------- | ---------------- | ------------ |
| projects                   | Project Management System | CSV    | Daily            | \~500 records    | Low          |
| employees                  | HR System                 | CSV    | Weekly           | \~1,000 records  | Low          |
| transactions               | Finance System            | CSV    | Daily            | \~50,000 records | Medium       |
| employees\_salary\_history | HR System                 | CSV    | Monthly          | \~10,000 records | Low          |

***

## **Section 2 — Data Classification**

###  Classification Definitions

| Classification | Definition                              |
| -------------- | --------------------------------------- |
| Public         | Non-sensitive, can be shared externally |
| Internal       | Internal use only                       |
| Confidential   | Sensitive business information          |
| Personal (PII) | Personally identifiable information     |

***

### 🔹 Column Classification

####  Projects Dataset

| Column               | Classification | Regulation |
| -------------------- | -------------- | ---------- |
| project\_id          | Internal       | None       |
| project\_name        | Internal       | None       |
| project\_manager\_id | Internal       | None       |
| budget               | Confidential   | None       |
| actual\_cost         | Confidential   | None       |
| start\_date          | Internal       | None       |
| end\_date            | Internal       | None       |

***

####  Employees Dataset

| Column       | Classification | Regulation      |
| ------------ | -------------- | --------------- |
| employee\_id | Internal       | None            |
| full\_name   | Personal (PII) | GDPR + UAE PDPL |
| email        | Personal (PII) | GDPR + UAE PDPL |
| department   | Internal       | None            |
| role         | Internal       | None            |
| salary       | Confidential   | UAE PDPL        |
| hiring\_date | Internal       | None            |

***

####  Transactions Dataset

| Column            | Classification | Regulation      |
| ----------------- | -------------- | --------------- |
| transaction\_id   | Internal       | None            |
| project\_id       | Internal       | None            |
| employee\_id      | Personal (PII) | GDPR + UAE PDPL |
| amount            | Confidential   | None            |
| transaction\_date | Internal       | None            |

***

####  Salary History Dataset

| Column          | Classification | Regulation      |
| --------------- | -------------- | --------------- |
| employee\_id    | Personal (PII) | GDPR + UAE PDPL |
| salary          | Confidential   | UAE PDPL        |
| effective\_date | Internal       | None            |

***

##  **Section 3 — Data Ownership**

| Dataset                    | Data Owner      | Data Steward  | Access Approver |
| -------------------------- | --------------- | ------------- | --------------- |
| projects                   | Product Manager | Data Engineer | CTO             |
| employees                  | HR Manager      | Data Engineer | HR Director     |
| transactions               | Finance Manager | Data Analyst  | CFO             |
| employees\_salary\_history | HR Director     | Data Engineer | HR Director     |

***

###  Explanation

* **Data Owner**: Responsible for overall data quality, governance, and business usage
* **Data Steward**: Responsible for maintaining, cleaning, and monitoring the data

***

## **Section 4 — Retention Policy**

| Dataset                    | Retention | Justification                                  | Disposal  | Enforcement      |
| -------------------------- | --------- | ---------------------------------------------- | --------- | ---------------- |
| projects                   | 5 years   | Business analytics & reporting                 | Archive   | Data Engineering |
| employees                  | 5 years   | HR compliance                                  | Anonymise | HR               |
| transactions               | 7 years   | Audit & financial regulations                  | Archive   | Finance          |
| employees\_salary\_history | 10 years  | Legal compliance (UAE labour law, audit needs) | Archive   | HR               |

***

###  Special Consideration

* Salary history requires **longer retention (10 years)** due to:
  * UAE labour law
  * Audit and compliance requirements
  * Historical compensation tracking

***

##  **Section 5 — Access Control**

| Persona       | Projects | Employees | Transactions | Salary History |
| ------------- | -------- | --------- | ------------ | -------------- |
| Data Engineer | Full     | Full      | Full         | Read           |
| BI Analyst    | Read     | Read      | Read         | None           |
| Finance Team  | Read     | None      | Full         | None           |
| HR Team       | None     | Full      | None         | Full           |
| Executive     | Read     | Read      | Read         | None           |

***

### 🔹 Access Philosophy

* Follow **least privilege principle**
* Salary data is **highly restricted**
* Only HR has full access to salary history

***

##  **Section 6 — Data Lineage**

```
Source Systems
   ↓
Raw CSV Files (datasets/)
   ↓
ETL Pipeline (etl_starter.py)
   ↓
Cleaned Data (outputs/)
   ↓
Data Warehouse / Reporting Layer
   ↓
Dashboards & Analysis






