## 4 Kubernetes Security Posture Management (Instructor demo)



## 4.1 Open the Security Posture Management App 

  <img src="../../assets/images/kspm-app.png" width="1400">

<br>

## 4.2 Navigate to the "Overview" Tab
- **Overview Screen**: Provides easy-to-understand main tiles representing each compliance standard.

- **Compliance Standards Tiles**: Offer an instant overview of the current status.

  <img src="../../assets/images/kspm-compliance-tiles.png" width="1400">

<br>

- **My Systems Tile**: Displays an overview of where Security Posture Management is enabled, showing status per cluster.

  <img src="../../assets/images/kspm-status-per-cluster.png" width="1400">

<br>

## 4.3. Explore Compliance Standards Tiles

  <img src="../../assets/images/kspm-tiles-drilldown.png" width="1400">


- **Drill-down Functionality**: Click on a tile to access deeper information.
- **Standards Available**:
  - CIS (Global)
  - DORA (EU Financial)
  - NIST (Non-critical GOV/Defense)
  - STIG (US DOD/GOV)

<br>

## 4.4 View Assessment Results for a Standard

- **Assessment Results Tab**: Displays individual rules for the selected standard.

  <img src="../../assets/images/kspm-results-tab.png" width="1400">

<br>

- **Filtering Options**: Filters to customize the view.
  - Filter by status (e.g., “Failed”).<br>

    <img src="../../assets/images/kspm-filtering-by-status.png" width="1400">

  - Filter by severity (e.g., “High”) to help prioritize resources.<br>

    <img src="../../assets/images/kspm-filtering-by-severity.png" width="1400">

<br>

- **Compliance Reporting**: Passed rules are also documented, which is essential for compliance reporting.<br>

  <img src="../../assets/images/kspm-compliance-report.png" width="1400">

<br>

### 4.5 Review Rule Details

  <img src="../../assets/images/kspm-details-side-panel.png" width="1400">

<br>

- **Rule Details Side Panel**: Provides more detailed information.
  - Indicates exactly where the system is failing.
  - Highlights the rule assessment.

  <img src="../../assets/images/kspm-assessment-details.png" width="800">

<br>

- **Access to Source and Version**: Displays the original source and version of the standard.

  <img src="../../assets/images/kspm-source-and-version.png" width="800">

<br>

### 4.6 Return to the "Overview" Tab
- Reiterate that this flow applies to each compliance standard.

  <img src="../../assets/images/kspm-app.png" width="1200">

<br>

### 4.7 Upcoming Enhancements

- **Integration with Kubernetes Data**: Future developments will allow users to connect ECR image scanning findings to monitored SPM data.

- **Additional Standards**: Engage with users to determine which standards would be beneficial for their organizations.