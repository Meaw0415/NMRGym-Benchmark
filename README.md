# NMRGym

A comprehensive benchmark suite for evaluating machine learning models on Nuclear Magnetic Resonance (NMR) prediction tasks.

🌐 **Live Demo**: [https://meaw0415.github.io/NMRGym-Benchmark](https://meaw0415.github.io/NMRGym-Benchmark)

📊 **Dataset**: [https://huggingface.co/datasets/meaw0415/NMRGym](https://huggingface.co/datasets/meaw0415/NMRGym)

## Evaluation scripts

Python entry points, input formats, metric definitions, reference-data export,
and runnable examples are documented in [docs/EVALUATION.md](docs/EVALUATION.md).
The metrics follow [NMRGym, arXiv:2601.15763v1](https://arxiv.org/abs/2601.15763v1),
Section 3.3. Run from this repository's root:

```bash
python -m pip install -r requirements-chem.txt
python -m unittest discover -s tests -v
bash scripts/evaluate_examples.sh
python -m nmrgym_eval --help
```

The examples write JSON reports to `results/`. Use your own reference files and
saved model predictions for evaluation; each report records input hashes and
the chosen evaluation settings.

## Overview

NMRGym provides standardized datasets and evaluation metrics for four key NMR prediction tasks:

1. **Structure Elucidation (NMR2Mol)** - Predict molecular structures from NMR spectra
2. **Functional Group Prediction (NMR2FG)** - Predict functional-group labels from NMR spectra
3. **Toxicity Prediction (NMR2Tox)** - Predict toxicity labels from NMR spectra
4. **Spectral Simulation (Mol2NMR)** - Predict ¹H and ¹³C peak positions from molecular structures

## Features

- 📊 Four comprehensive benchmark tasks
- 🏆 Interactive leaderboards for model comparison
- 📈 Standardized evaluation metrics
- 🔬 10,000+ molecules with NMR data
- 📱 Responsive design for all devices
- 🚀 Easy deployment to GitHub Pages

## Quick Start

### View the Website Locally

1. Clone this repository:
```bash
git clone https://github.com/Meaw0415/NMRGym-Benchmark.git
cd NMRGym-Benchmark
```

2. Open `index.html` in your web browser:
```bash
# On macOS
open index.html

# On Linux
xdg-open index.html

# On Windows
start index.html
```

Or use a local web server:
```bash
# Python 3
python -m http.server 8000

# Python 2
python -m SimpleHTTPServer 8000

# Node.js (with http-server installed)
npx http-server
```

Then navigate to `http://localhost:8000`

### Deploy to GitHub Pages

1. Create a new repository on GitHub named `NMRGym-Benchmark`

2. Initialize git and push your code:
```bash
cd NMRGym-Benchmark
git init
git add .
git commit -m "Initial commit: NMRGym website"
git branch -M main
git remote add origin https://github.com/Meaw0415/NMRGym-Benchmark.git
git push -u origin main
```

3. Enable GitHub Pages:
   - Go to your repository on GitHub
   - Click on **Settings** > **Pages**
   - Under **Source**, select `main` branch and `/ (root)` folder
   - Click **Save**

4. Your site will be published at: `https://meaw0415.github.io/NMRGym-Benchmark`

## Project Structure

```
NMRGym-Benchmark/
├── index.html          # Main HTML file
├── css/
│   └── style.css      # Stylesheet
├── js/
│   └── main.js        # JavaScript for interactivity
├── images/            # Image assets (add your images here)
├── data/              # Dataset files (optional)
├── README.md          # This file
└── .gitignore         # Git ignore file
```

## Customization

### Update Content

- **Tasks**: Edit the benchmark tasks in `index.html` (search for "benchmark-card")
- **Leaderboard**: Update model rankings in `js/main.js` (leaderboardData object)
- **Styling**: Modify colors and design in `css/style.css`
- **Metrics**: Change evaluation metrics in the task detail sections

### Add Your Logo

1. Add your logo image to the `images/` folder
2. Update the header in `index.html`:
```html
<div class="logo">
    <img src="images/your-logo.png" alt="Logo">
    <h1>NMR Prediction Benchmark</h1>
</div>
```

### Change Color Scheme

Edit the CSS variables in `css/style.css`:
```css
:root {
    --primary-color: #2563eb;    /* Your primary color */
    --secondary-color: #1e40af;  /* Your secondary color */
    --accent-color: #3b82f6;     /* Your accent color */
}
```

## Contributing

We welcome contributions! Please feel free to submit a Pull Request.

### How to Contribute

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Dataset

Dataset files are hosted on [Hugging Face](https://huggingface.co/datasets/meaw0415/NMRGym).
See [the evaluation guide](docs/EVALUATION.md#reference-data) for a versioned
download example, checksum, and JSONL export commands.

## Citation

If you use this benchmark in your research, please cite:

```bibtex
@article{nmr-benchmark-2025,
  title={NMR Prediction Benchmark: A Comprehensive Evaluation Suite},
  author={Your Name et al.},
  journal={Journal Name},
  year={2025}
}
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## About

NMRGym is developed and maintained by the **AIMS Lab** (AI for Molecule and Science) at **The Hong Kong University of Science and Technology (Guangzhou)**.

- **AIMS Lab**: [https://github.com/AIMS-HKUSTGZ](https://github.com/AIMS-HKUSTGZ)
- **PI Homepage**: [https://junxia97.github.io/](https://junxia97.github.io/)

## Contact

- **Students**: zfang723@connect.hkust-gz.edu.cn
- **Principal Investigator**: junxia@hkust-gz.edu.cn
- **GitHub Issues**: [https://github.com/Meaw0415/NMRGym-Benchmark/issues](https://github.com/Meaw0415/NMRGym-Benchmark/issues)

## Acknowledgments

- Inspired by [ProteinGym](https://proteingym.org)
- Built with HTML, CSS, and vanilla JavaScript
- Fonts from Google Fonts (Inter)

---

**Made with ❤️ by AIMS Lab, HKUST(GZ) for the computational chemistry community**
