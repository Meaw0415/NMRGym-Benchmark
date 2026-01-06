# Data Directory

This directory is intended to store benchmark datasets and related files.

## Recommended Structure

```
data/
├── task1_chemical_shift/
│   ├── train.csv
│   ├── val.csv
│   ├── test.csv (hidden/not included)
│   └── README.md
├── task2_coupling_constant/
│   ├── train.csv
│   ├── val.csv
│   ├── test.csv (hidden/not included)
│   └── README.md
├── task3_spectrum_reconstruction/
│   ├── train/
│   ├── val/
│   ├── test/ (hidden/not included)
│   └── README.md
└── task4_structure_elucidation/
    ├── train/
    ├── val/
    ├── test/ (hidden/not included)
    └── README.md
```

## Data Format Examples

### Task 1: Chemical Shift Prediction

CSV format with columns:
- `molecule_id`: Unique identifier
- `smiles`: SMILES string of the molecule
- `atom_index`: Index of the atom
- `chemical_shift`: Chemical shift value (ppm)
- `nucleus`: Type of nucleus (1H or 13C)

### Task 2: Coupling Constant Prediction

CSV format with columns:
- `molecule_id`: Unique identifier
- `smiles`: SMILES string
- `atom_i`: First atom index
- `atom_j`: Second atom index
- `coupling_constant`: J-coupling value (Hz)
- `coupling_type`: Type (1J, 2J, 3J)

### Task 3: Spectrum Reconstruction

Directory structure with:
- `{molecule_id}.json`: Contains molecule info and spectrum array
- Format: `{"smiles": "...", "spectrum": [...]}`

### Task 4: Structure Elucidation

Directory structure with:
- `{molecule_id}_spectrum.json`: Input NMR spectrum data
- `{molecule_id}_structure.smi`: Target SMILES structure

## Note

The actual dataset files are not included in this repository. They will be made available for download separately.

For access to the datasets, please visit the website or contact the maintainers.
