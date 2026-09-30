---
license: cc-by-sa-4.0
dataset_info:
  features:
  - name: document_id
    dtype: string
  - name: age
    dtype: int64
  - name: gender
    dtype: string
  - name: test_name
    dtype: string
  - name: display_ranges
    dtype: string
  - name: value
    dtype: string
  - name: unit
    dtype: string
  - name: specimen
    dtype: string
  - name: loinc
    dtype: string
  splits:
  - name: train
    num_bytes: 871016637
    num_examples: 6844304
  download_size: 175616483
  dataset_size: 871016637
configs:
- config_name: default
  data_files:
  - split: train
    path: data/train-*
language:
- en
tags:
- Lab
- Vitals
- EkaCare
- IndiaAI
- Diagnostics
- Investigations
- India
- Parrotlet
pretty_name: NidaanKosha
size_categories:
- 1M<n<10M
---

# NidaanKosha
## A Comprehensive Laboratory Investigation Dataset of 100,000 Indian Subjects with 6.8 Million+ Readings

> In Sanskrit, "Nidaan" (निदान) signifies "diagnosis" or "investigation," while "Kosha" (कोष) represents a "treasury" or "repository." Together, NidaanKosha embodies a valuable collection of diagnostic information, preserving vital health insights for research and innovation.

## Dataset Overview

NidaanKosha is an extensive repository containing laboratory investigation readings from 100,000 lab reports collected across diverse diagnostic facilities throughout India. This comprehensive dataset represents a curated collection of data extracted through Eka Care's Parrotlet vision LLM, which automatically parse images and PDFs to extract structured health information. The dataset contains approximately 6.8 million individual investigation readings, each mapped to standardized LOINC identifiers for interoperability.

- **Curated and Shared by:** [Eka.Care](https://www.eka.care/)
- **License:** [CC-BY-SA-4.0](https://creativecommons.org/licenses/by-sa/4.0/deed.en)

## Data Acquisition

The laboratory investigation readings were extracted from lab reports collected through Eka Care's Personal Health Record applications:

- **Applications:** Eka Care PHR mobile applications 
  - [iOS app](https://apps.apple.com/in/app/eka-care-abha-health-records/id1561621558)
  - [Android app](https://play.google.com/store/apps/details?id=eka.care&hl=en_IN&pli=1)

## Data Structure and Parameters

The dataset provides a rich collection of laboratory investigation readings with the following key attributes:

### Core Components
- **document_id:** Unique identifier for each lab report
- **age:** Age of the subject (as specified in the report)
- **gender:** Gender of the subject (as specified in the report)
- **test_name:** Extracted name of the lab investigation from the report
- **value:** Measured value of the investigation
- **unit:** Unit of measurement for the investigation value
- **display_ranges:** Reference range for the specific investigation (specified in the row of the lab test, these readings are not read from the reference range table often provided in lab reports)
- **specimen:** Identified Specimen of the lab investigation
- **loinc:** LOINC code of the lab investigation (Automatically done)

### Demographic Information
- Gender-balanced dataset to ensure representative insights
- Geographic distribution across various regions in India

## Extraction Methodology

### Parrotlet AI Model Series
The laboratory values were automatically extracted using Eka Care's proprietary Parrotlet series of AI models, specifically designed to:
- Parse both image and PDF formats of lab reports
- Identify and extract relevant investigation parameters
- Map extractions to standardized LOINC codes
- Maintain high accuracy and reliability in data extraction

## Potential Applications

- Population health studies specific to Indian demographics
- Medical research on reference ranges in Indian populations
- Benchmarking and improving laboratory data extraction models
- Training and validation of health data interoperability systems

## Dataset Creation Methodology

### Data Collection and Processing

The shared corpus is a carefully selected subset of data collected through Eka Care's PHR applications. The dataset has been curated to ensure diversity across gender and geographic representation while maintaining quality and completeness of extracted information.

### Privacy Considerations

This dataset contains absolutely no personally identifiable information (PII) and is completely anonymized. All document identifiers have been randomized to prevent any connection to original users.

## References
- [Lab-Ready and Prescription-Perfect: Eka Care's Small LLMs vs. Industry Giants](https://info.eka.care/services/lab-ready-and-prescription-perfect-ekas-small-llms-vs-industry-giants)
- [Extracting Structured Information from Lab Reports: Challenges and Learnings](https://info.eka.care/services/eka-smart-report)

#### Examples of Studies done with dataset
- [The Quiet Threat: Understanding Latent Iron Deficiency](https://www.eka.care/services/the-quiet-threat-understanding-latent-iron-deficiency)
- [Cholesterol Chronicles - The Indian Disadvantage](https://info.eka.care/services/cholesterol-chronicles-the-indian-disadvantage-2)


## Contact Information

For inquiries, please email with the subject line "NidaanKosha enquiry" to: sankalp [at] eka.care