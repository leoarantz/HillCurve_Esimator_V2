# Hill Curve Estimator — v2

Windows desktop GUI for a single-stage Hill/Ramberg-Osgood tensile stress-strain estimate.

## Features
- Inputs: E, yield/0.2% proof stress, UTS, maximum elongation, number of curve points.
- Automatic Hill exponent n calculation.
- Estimated true stress-true strain curve.
- Paste two columns from Excel: true strain and true stress.
- Overlay test data with the estimated curve.
- Save plot and export estimated curve CSV.
- **Abaqus Material Card tab:** view the generated material definition, edit it manually, copy it, or export it as a `.inp` file.

## Abaqus card
The generated card uses `*ELASTIC` and `*PLASTIC`. The plastic table contains true stress and true plastic strain derived from the estimated Hill curve. The default Poisson ratio is 0.3 and is editable in the material-card text area before export.

The exported `.inp` contains exactly the text currently shown in the editable material-card box.

## Build with GitHub Actions
1. Upload all files/folders in this project to the root of a GitHub repository.
2. Go to **Actions**.
3. Select **Build Windows EXE**.
4. If it did not run automatically, select **Run workflow**.
5. After the run is green, download the artifact **HillCurveEstimator-Windows**.
