import pandas as pd
import json
import os
import re
import shutil
import tempfile
from typing import Dict, Optional

class SectionDatabase:
    def __init__(self):
        self.tables = {}
    
    def load_all_tables(self, folder_path: str = "."):
        """Load both UC and UB tables"""
        uc_file = "UC-secpropsdimsprops-EC3UKNA-UK-1-31-2026.xlsx"
        ub_file = "UB-secpropsdimsprops-EC3UKNA-UK-1-31-2026.xlsx"
        
        files = {
            "UC": os.path.join(folder_path, uc_file),
            "UB": os.path.join(folder_path, ub_file)
        }
        
        for section_type, file_path in files.items():
            if os.path.exists(file_path):
                try:
                    self.tables[section_type] = self._load_single_table(file_path)
                    print(f"✅ Loaded {len(self.tables[section_type])} {section_type} sections")
                except Exception as e:
                    print(f"❌ Failed to load {section_type} table from {file_path}: {e}")
            else:
                print(f"⚠️  {file_path} not found")
    
    def _load_single_table(self, path: str) -> pd.DataFrame:
        """Load and clean Excel table"""
        # Create a temp copy to avoid file locking issues (PermissionError)
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
                temp_path = tmp.name
            shutil.copyfile(path, temp_path)
            read_path = temp_path
        except Exception as e:
            print(f"⚠️ Could not create temp copy of {path}: {e}. Trying original.")
            read_path = path

        try:
            raw = pd.read_excel(read_path, header=None)
            header_row_idx = raw.index[
                raw.iloc[:, 0].astype(str).str.contains('Section designation', na=False)
            ][0]
            
            df = pd.read_excel(read_path, header=header_row_idx + 1)
        finally:
            if read_path != path and os.path.exists(read_path):
                try:
                    os.remove(read_path)
                except:
                    pass

        first_col = df.columns[0]
        df = df.rename(columns={first_col: 'Section designation'})
        # Rename ambiguous 'Unnamed' columns to meaningful names
        col_map = {
            'Unnamed: 0': 'extra_col_0',
            'Unnamed: 1': 'section_designation_extra',
            'Unnamed: 2': 'extra_col_2',
            # Main Dimensions
            'Mass per metre': 'Mass per metre        kg/m',
            'Depth of section': 'Depth of section      h (mm)',
            'Width of section': 'Width of section      b (mm)',
            'Thickness': 'Web thickness         tw (mm)',
            'Unnamed: 7': 'Flange thickness      tf (mm)',
            'Root radius': 'Root radius           r (mm)',
            'Depth between fillets': 'Depth between fillets d (mm)',
            # Ratios
            'Ratios for local buckling': 'cw / tw (Web slenderness ratio)',
            'Unnamed: 11': 'cf / tf (Flange slenderness ratio)',
            # Dimensions for detailing
            'Dimensions for detailing': 'C (End clearance) (mm)',
            'Unnamed: 13': 'N (Notch distance) (mm)',
            'Unnamed: 14': 'n (Notch distance) (mm)',
            # Surface Area
            'Surface area': 'Surface area (Per metre) (m²/m)',
            'Unnamed: 16': 'Surface area (Per tonne) (m²/t)',
            # Second Moment of Area
            'Second moment of area': 'Second moment of area (Axis y-y) (Iy) (cm⁴)',
            'Unnamed: 18': 'Second moment of area (Axis z-z) (Iz) (cm⁴)',
            # Radius of Gyration
            'Radius of gyration': 'Radius of gyration (Axis y-y) (ry) (cm)',
            'Unnamed: 20': 'Radius of gyration (Axis z-z) (rz) (cm)',
            # Elastic Modulus
            'Elastic modulus': 'Elastic modulus (Axis y-y) (W_el,y) (cm³)',
            'Unnamed: 22': 'Elastic modulus (Axis z-z) (W_el,z) (cm³)',
            # Plastic Modulus
            'Plastic modulus': 'Plastic modulus (Axis y-y) (W_pl,y) (cm³)',
            'Unnamed: 24': 'Plastic modulus (Axis z-z) (W_pl,z) (cm³)',
            # Properties
            'Buckling parameter': 'Buckling parameter (u)',
            'Torsional index': 'Torsional index (x)',
            'Warping constant': 'Warping constant (Iw) (dm⁶)',
            'Torsional constant': 'Torsional constant (IT) (cm⁴)',
            'Area of section': 'Area of section (A) (cm²)'
        }
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
        
        # Propagate the section designation downwards for grouped rows (e.g. mass variations)
        # because the first column 'Section designation' might be empty for subsequent rows in a group.
        df['Section designation'] = df['Section designation'].ffill()
        
        df = df.dropna(subset=['Section designation'])
        # Create normalized lookup key (depth x width)
        # Create normalized lookup keys:
        # - `lookup_key`: always the first two numeric parts joined with 'x' (e.g. '1016x305')
        # - `full_lookup_key`: if present, include the third numeric part (e.g. '1016x305x584')
        def build_keys(s):
            txt = str(s) if pd.notna(s) else ''
            nums = re.findall(r"\d+(?:\.\d+)?", txt)
            key2 = ''
            key3 = ''
            if len(nums) >= 2:
                key2 = f"{nums[0]}x{nums[1]}"
            if len(nums) >= 3:
                key3 = f"{nums[0]}x{nums[1]}x{nums[2]}"
            return pd.Series({'lookup_key': key2.lower(), 'full_lookup_key': key3.lower()})

        keys = df['Section designation'].apply(build_keys)
        df = pd.concat([df, keys], axis=1)

        # If the sheet uses a second column to hold the trailing 'x NNN' piece,
        # standardize its name earlier (we renamed some Unnamed columns above).
        if 'section_designation_extra' in df.columns:
            # extract numeric from extra column (e.g. 'x 584' -> 584.0)
            def extra_num(v):
                if pd.isna(v):
                    return None
                m = re.search(r"(\d+(?:\.\d+)?)", str(v))
                return float(m.group(1)) if m else None
            df['extra_numeric'] = df['section_designation_extra'].apply(extra_num)
        else:
            df['extra_numeric'] = None
        return df
    
    def find_section(self, input_string: str) -> Dict:
        """Parse input like 'uc 356x406x1299' or 'ub 1016x305x584'"""
        input_lower = input_string.lower().strip()
        # Built-up H (I) section shortcut: 'h D x B x T x t' (e.g. 'h 300x150x20x10')
        m_h = re.match(r"^\s*h\s*[,\s]*(.+)$", input_lower)
        if m_h:
            designation = m_h.group(1).strip()
            parts = re.split(r'[x×\s,]+', designation)
            if len(parts) < 4:
                raise ValueError("H-section requires 4 dimensions: D x B x T x t (e.g. 'h 300x150x20x10')")
            try:
                D, B, T, t = map(float, parts[:4])
            except Exception:
                raise ValueError("Could not parse H-section dimensions as numbers")
            A, Ixx = self._h_section_properties(D, B, T, t)
            return {
                "type": "H-BuiltUp",
                "section": f"h {designation}",
                "properties": {
                    "Area (A) (mm^2)": A,
                    "Second moment of area (Ixx) (mm^4)": Ixx,
                }
            }

        # Accept formats like: 'uc 356x406x1299', 'ub,914x305x576', 'uc, 356x406'
        m = re.match(r"^\s*(uc|ub)\s*[,\s]*(.+)$", input_lower)
        if not m:
            raise ValueError("Input must start with 'uc' or 'ub' followed by a designation, e.g. 'uc 356x406' or 'ub,914x305x576'")

        section_type = m.group(1).upper()
        designation = m.group(2).strip()
        
        # Verify table exists
        if section_type not in self.tables:
            raise ValueError(f"{section_type} table not loaded")
        
        # Find section
        df = self.tables[section_type]

        # Normalize designation into parts (depth x width [x mass/other])
        parts = re.split(r'[x×\s,]+', designation)
        if len(parts) >= 2:
            key = (parts[0] + 'x' + parts[1]).replace(' ', '').lower()
        else:
            key = designation.replace(' ', '').lower()

        # Prefer exact two-part matches first
        matches = df[df['lookup_key'] == key]

        # If nothing found, fall back to contains (robustness)
        if matches.empty:
            matches = df[df['lookup_key'].str.contains(key, na=False)]

        if matches.empty:
            raise ValueError(f"{section_type} section '{designation}' not found")

        # If a third part is provided (e.g. mass), try to refine the match using
        # (in order): full_lookup_key, extra_numeric, or section_designation_extra text.
        if len(parts) >= 3:
            third_raw = parts[2]
            # try numeric parse
            third_val = None
            try:
                third_val = float(third_raw)
            except Exception:
                third_val = None

            # 1) match full_lookup_key exactly
            if third_raw and any(matches['full_lookup_key'].astype(str).str.len() > 0):
                full_key = (parts[0] + 'x' + parts[1] + 'x' + parts[2]).replace(' ', '').lower()
                fk_matches = matches[matches['full_lookup_key'] == full_key]
                if not fk_matches.empty:
                    row = fk_matches.iloc[0]
                    return {"type": section_type, "section": designation, "properties": self._format_row(row.drop(['lookup_key','full_lookup_key']))}

            # 2) match numeric extra column
            if third_val is not None and 'extra_numeric' in matches.columns:
                en_matches = matches[matches['extra_numeric'].notna() & (matches['extra_numeric'] == third_val)]
                if not en_matches.empty:
                    row = en_matches.iloc[0]
                    return {"type": section_type, "section": designation, "properties": self._format_row(row.drop(['lookup_key','full_lookup_key']))}

            # 3) match textual 'section_designation_extra' normalized (e.g. 'x584')
            if 'section_designation_extra' in matches.columns:
                norm = f"x{str(third_raw).strip().replace(' ','').lower()}"
                te_matches = matches[matches['section_designation_extra'].astype(str).str.strip().str.replace(r'\s+','',regex=True).str.lower() == norm]
                if not te_matches.empty:
                    row = te_matches.iloc[0]
                    return {"type": section_type, "section": designation, "properties": self._format_row(row.drop(['lookup_key','full_lookup_key']))}

        # Fallback: return first match
        row = matches.iloc[0]
        return {
            "type": section_type,
            "section": designation,
            "properties": self._format_row(row.drop('lookup_key'))
        }
    
    def _format_row(self, row) -> Dict:
        return {k: v for k, v in row.items() if pd.notna(v)}

    def _h_section_properties(self, D: float, B: float, T: float, t: float):
        """
        Compute cross-sectional area and second moment of area Ixx for a symmetric H (I) section.

        Parameters:
          D : total depth (overall height) of the section
          B : flange width (length of each flange)
          T : flange thickness (thickness of top and bottom flange)
          t : web thickness (thickness of vertical web)

        Returns:
          A  : total cross-sectional area (same units as inputs squared)
          Ixx: second moment of area about the horizontal centroidal axis (same units as inputs^4)
        """

        # Areas of components
        A_flange = B * T
        A_top = A_flange
        A_bot = A_flange
        A_web = t * (D - 2.0 * T)

        # Total area
        A = A_top + A_bot + A_web

        # vertical positions of flange centroids from mid-height (symmetric => web centroid at 0)
        y_top = (D / 2.0) - (T / 2.0)
        y_bot = -y_top

        # Second moment of area of each rectangle about its own centroidal horizontal axis
        I_top_centroid = (B * (T ** 3)) / 12.0
        I_bot_centroid = I_top_centroid
        I_web_centroid = (t * ((D - 2.0 * T) ** 3)) / 12.0

        # Use parallel-axis theorem
        I_top = I_top_centroid + A_top * (y_top ** 2)
        I_bot = I_bot_centroid + A_bot * (y_bot ** 2)
        I_web = I_web_centroid  # web centroid at 0

        Ixx = I_top + I_bot + I_web

        return A, Ixx

# Simple lookup function
def lookup_section(input_string: str):
    db = SectionDatabase()
    db.load_all_tables()
    return db.find_section(input_string)

# Interactive mode
def interactive_test():
    db = SectionDatabase()
    db.load_all_tables()
    
    print("\n🎮 Interactive Section Lookup")
    print("Format: 'uc 356x406x1299' or 'ub 1016x305x584'")
    print("Type 'quit' to exit")
    
    while True:
        user_input = input("\n> ").strip()
        if user_input.lower() == 'quit':
            break
        
        try:
            result = db.find_section(user_input)
            print(f"\n✅ Found {result['type']} {result['section']}")
            print("-" * 50)
            
            props = result['properties']
            for param, value in list(props.items())[:12]:  # First 12 properties
                print(f"  {param}: {value}")
            print(f"  ... + {len(props)-12} more properties")
            
        except ValueError as e:
            print(f"❌ {e}")

# FastAPI version
def create_fastapi_app():
    db = SectionDatabase()
    db.load_all_tables()
    
    from fastapi import FastAPI, HTTPException
    app = FastAPI()
    
    @app.get("/section/{input_string}")
    async def get_section(input_string: str):
        try:
            result = db.find_section(input_string)
            return result
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
    
    return app

# Test it
if __name__ == '__main__':
    print("🔗 Steel Section Lookup (UC/UB)")
    
    # Test your examples
    tests = [
        "ub 1016x305x584",
        "uc 356x406x1299", 
        "UC 305x305x283"
    ]
    
    db = SectionDatabase()
    db.load_all_tables()
    
    for test in tests:
        try:
            result = db.find_section(test)
            print(f"✅ {test} → {result['type']}: {len(result['properties'])} properties")
        except:
            print(f"❌ {test} failed")
    
    print("\n🎮 Run interactive_test() to try it yourself!")
