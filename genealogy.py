"""
genealogy.py module: people's parents, marriages, etc.
(also deals with household information from the master sheet file)

utilities for parsing, consistency-checking, and manipulating data from
  CSV files exported from spreadsheets of the following types:

 (1) the *Identities* type (a.k.a. the *BirthParents* type), e.g.
      "IdentitiesChinguo.csv" or "IndividualBirthParentsChinguo.csv";
 (2) the *Marriage* type, e.g. "ChinguoMarriage.csv" or the
      contradictorily-named "IndividualChinguoMarriage.csv";
 (3) the MasterSheet type, e.g. "IndividualDataMasterSheet.csv"

*Identities*: Column names are currently:
  "Name","ID Number","Sex","Other Names","Identity Notes",
  "Best Date Of Birth","Year of Birth","Year of Death",
  "Name of father","Father ID","Name of Mother","Mother ID",
  "Legitimacy"

*Marriage*: Column names are currently:
  Husband Name,Husband ID Number,Wife Name,Wife ID Number,
  Marriage Type,Date of Marriage,Date First Child's Birth,
  Date of Divorce,Date of Widow-hood

*MasterSheet*: Links IDs to household membership in various years.  Relevant
  column names:  Number,Hhold N 1986,Hhold 1992,Hhold 1999,Hhold 2010
  (note anomalous 1986 column name containing "N")
"""
import csv
import os

# Constants to define CSV file locations
#  * Original data needs to be anonymized for analysis, but we need access to
#     real names for verifying data accuracy
#  * "IBP" = "IndividualBirthParents" = identity-type information
#  * "MARR" = marriage information
#  * "HH" = household information

BASE_DIR = os.path.abspath("%s/.." % os.path.dirname(os.path.abspath(__file__)))
IBP_FILENAME = "derived-data/IdentitiesChinguo.csv"
ANON_IBP_FILENAME = "derived-data/ANON-IdentitiesChinguo.csv"
MARR_FILENAME = "derived-data/ChinguoMarriage.csv"
HH_FILENAME = "derived-data/IndividualDataMasterSheet.csv"

DEFAULT_IBP = "%s/%s" % (BASE_DIR, IBP_FILENAME)
ANON_IBP = "%s/%s" % (BASE_DIR, ANON_IBP_FILENAME)
DEFAULT_MARR = "%s/%s" % (BASE_DIR, MARR_FILENAME)
DEFAULT_HH = "%s/%s" % (BASE_DIR, HH_FILENAME)


def verify_ibp(filename=DEFAULT_IBP, print_errors=True):
  """
  Stand-alone consistency checker and potential error locator function for
  IBP (identity) file data.

  Params:
    filename (str) - CSV to read; must have format described in module comments
    print_errors (boolean) - if False, data errors raise ValueError; if True,
       data errors are printed and the function returns True iff there are none

  Returns:
    True iff no errors are detected in the file; otherwise return False or
    raise ValueError as per the print_errors parameter
  """
  data, errors = {}, []

  # Step 1: Parse the CSV, flagging missing ID numbers, duplicate ID numbers,
  # and missing names.

  with open(filename) as f:
    reader = csv.DictReader(f)
    for row in reader:
      if all(not val for val in row.values()):
        continue   # ignore blank row
      if not row["ID Number"]:
        errors.append("Partially blank line missing ID number: %r" % row)
        continue
      if row["ID Number"] in data:
        errors.append("duplicate ID: %s (%r and %r)" % (
            row["ID Number"], row["Name"], data[row["ID Number"]]["Name"]))
        continue
      if not row["Name"]:
        errors.append("No name for ID %s" % row["ID Number"])
      data[row["ID Number"]] = row

  # Step 2: Verify that all listed ID numbers for each individual's parents are
  # actual ID numbers of real people.  If an individual's parents are not
  # known, they should be left blank.  In fact, if an individual's parents are
  # simply not relevant to the analysis because they aren't in any path of
  # kinship, they may be left blank.
  #
  # Also verify that the parents' names, which are redundantly listed next to
  # their IDs, match the names associated with those IDs.  This helps catch
  # data errors.

  for idnum in data:
    mid, fid = data[idnum]["Mother ID"], data[idnum]["Father ID"]
    if mid:
      if mid not in data:
        errors.append("%s (%s): non-existent Mother ID (%s)" % (
            data[idnum]["Name"], idnum, mid))
      else:
        valid_mnames = [data[mid]["Name"]] + [
          n.strip() for n in data[mid]["Other Names"].split(";") if n.strip()]
        if len(valid_mnames) == 1 and any(s in valid_mnames[0] for s in (
            'father', 'Father', 'mother', 'Mother')):
          valid_mnames.append("Unknown")
        if data[idnum]["Name of Mother"] not in valid_mnames:
          err = "Name discrepency: %r not in %r" % (
              data[idnum]["Name of Mother"], valid_mnames)
          if err not in errors: errors.append(err)
    if fid:
      if fid not in data:
        errors.append("%s (%s): non-existent Father ID (%s)" % (
            data[idnum]["Name"], idnum, fid))
      else:
        valid_fnames = [data[fid]["Name"]] + [
          n.strip() for n in data[fid]["Other Names"].split(";") if n.strip()]
        if len(valid_fnames) == 1 and any(s in valid_fnames[0] for s in (
            'father', 'Father', 'mother', 'Mother')):
          valid_fnames.append("Unknown")
        if data[idnum]["Name of father"] not in valid_fnames:
          err = "Name discrepency: %r not in %r" % (
              data[idnum]["Name of father"], valid_fnames)
          if err not in errors: errors.append(err)

  # Report errors and indicate result (through return value or exception)

  if errors:
    if print_errors:
      print "\n".join(sorted(errors))
      return False
    else:
      raise ValueError(sorted(errors))
  return True


def verify_marriages(filename=DEFAULT_MARR, print_errors=True):
  """
  Stand-alone consistency checker and potential error locator function for
  marriage file data.  Relies on IBP (identity) file for canonical information
  about individuals.

  Params:
    filename (str) - CSV to read; must have format described in module comments
    print_errors (boolean) - if False, data errors raise ValueError; if True,
       data errors are printed and the function returns True iff there are none

  Returns:
    True iff no errors are detected in the file; otherwise return False or
    raise ValueError as per the print_errors parameter
  """
  ibp = get_ibp_data_from_file(filename=DEFAULT_IBP, ignore_errors=True)
  errors = []

  # Parse the CSV, flagging errors

  with open(filename) as f:
    reader = csv.DictReader(f)
    for row in reader:
      if all(not val for val in row.values()):
        continue   # ignore blank rows

      # Check for missing or invalid ID numbers for husband/wife

      hid, wid = row["Husband ID Number"], row["Wife ID Number"]
      if not hid or not wid:
        errors.append("Missing husband or wife ID number: %r" % row)
        continue
      if hid not in ibp:
        errors.append("non-existent ID in marriage: %s (%s)" % (
            hid, row["Husband Name"]))
        continue
      if wid not in ibp:
        errors.append("non-existent ID in marriage: %s (%s)" % (
            wid, row["Wife Name"]))
        continue

      # Check for incorrect sex for husband/wife
      # (Traditional gender roles in this culture; discrepancies are data errors
      # rather than non-traditional marriages.)

      if ibp[hid]["sex"] != 'M':
        errors.append("%s: Husband is not male" % marriage_name)
      if ibp[wid]["sex"] != 'F':
        errors.append("%s: Wife is not female" % marriage_name)

      # Verify names against expected names for the IDs -- another way to check
      # for data errors.

      if row["Husband Name"] != ibp[hid]["name"]:
          errors.append("Name discrepency: %r vs. %r" % (
              ibp[hid]["name"], row["Husband Name"]))
      if row["Wife Name"] != ibp[wid]["name"]:
          errors.append("Name discrepency: %r vs. %r" % (
              ibp[wid]["name"], row["Wife Name"]))

  # Report errors and indicate result (through return value or exception)

  if errors:
    if print_errors:
      print "\n".join(errors)
      return False
    else:
      raise ValueError(errors)
  return True


def get_ibp_data_from_file(filename=DEFAULT_IBP, ignore_errors=False):
  """
  Parse the IBP (identity) file and return the data indexed by ID number.

  Params:
    filename (str) - CSV to read; must have format described in module comments
    ignore_errors (boolean) - if True, ignore data errors (action on erroneous
      data is undefined); if False, raise ValueError

  Returns:
    a dict with the format {idnum: {field1: value1, ...}, ...}
    fields are:
      name, sex, birthyear, best_dob, best_dod, father_id, mother_id, legitimacy
    father_id and mother_id can be used to generate the kinship network
  """
  data = {}
  with open(filename) as f:
    reader = csv.DictReader(f)
    for row in reader:
      if all(not val for val in row.values()):
        continue   # ignore blank row
      if row["ID Number"] in data:
        if ignore_errors:
          continue  # current impl: with dup IDs, first version wins
        else:
          raise ValueError("duplicate ID: %s (%r and %r)" % (
              row["ID Number"], row["Name"], data[row["ID Number"]]["name"]))
      fid = int(row["Father ID"]) if row["Father ID"] else None
      mid = int(row["Mother ID"]) if row["Mother ID"] else None
      name = row["Name"] if "Name" in row else 'Person %s' % row["ID Number"]
      data.update({
          int(row["ID Number"]): {
            "name": name,
            "sex": row["Sex"].upper(),
            "birthyear": row["Year of Birth"],
            "best_dob": row["Best Date Of Birth"] or row["Year of Birth"],
            "best_dod": row["Year of Death"],
            "father_id": fid,
            "mother_id": mid,
            "legitimacy": row["Legitimacy"],
          }
        })

  return data


def get_marriage_data_from_file(filename=DEFAULT_MARR, ignore_errors=False):
  """
  Parse the marriage file and return the data indexed by (ID1, ID2) pair.
  (Lower ID number first, regardless of sex.)

  Params:
    filename (str) - CSV to read; must have format described in module comments
    ignore_errors (boolean) - if True, ignore data errors (action on erroneous
      data is undefined); if False, raise ValueError

  Returns:
    a pair of dicts: (indivs_to_marriages, marriage_data)
    indivs_to_marriages:
        dict mapping individual IDs to a list of all their marriage-pairs
    marriage_data:
        a dict with the format {id_pair: {field1: value1, ...}, ...}
        fields are:
          husband_id, wife_id, marriage_type, marriage_date, marriage_end_date,
          marriage_end_reason
    marriage ID pairs can be used (with father/mother IDs) to generate the
      kinship network
  """
  indivs_to_marriages, marriage_data = {}, {}
  with open(filename) as f:
    reader = csv.DictReader(f)
    for row in reader:
      if all(not val for val in row.values()):
        continue   # ignore blank row
      hid, wid = row["Husband ID Number"], row["Wife ID Number"]
      if not hid or not wid:
        if ignore_errors:
          continue
        else:
          raise ValueError("Missing husband or wife ID number: %r" % row)
      hid, wid = int(hid), int(wid)

      id_pair = (hid, wid) if hid < wid else (wid, hid)
      indivs_to_marriages.setdefault(hid, []).append(id_pair)
      indivs_to_marriages.setdefault(wid, []).append(id_pair)
      marriage_data[id_pair] = {
        'husband_id': hid,
        'wife_id': wid,
        'marriage_type': row["Marriage Type"] or 'standard',
        'marriage_date': (
            row["Date of Marriage"] or row["Date First Child's Birth"] or None),
        'marriage_end_date': (
            row["Date of Divorce"] or row["Date of Widow-hood"] or None),
        'marriage_end_reason': (
            'divorce' if row["Date of Divorce"] else
               'death of spouse' if row["Date of Widow-hood"] else None),
      }

  return indivs_to_marriages, marriage_data


def canonical_hh(val):
  """
  Data-cleaning function to return the canonical name of a household.

  Params:
    val (str) - the uncleaned household name, e.g. "3.00"

  Returns: (str) the cleaned household name, e.g. "3"
  """
  if type(val) in (int, float): return val
  if val == '': return None
  if val == '3/3.1': return '3.1'   # special case, occurs once in the data
  floatval = float(val)
  if floatval == int(floatval): return '%d' % int(floatval)
  return '%.1f' % floatval


def get_household_membership_from_file(
    filename=DEFAULT_HH, ignore_errors=False):
  """
  Parse the MasterSheet file and return a mapping of individual IDs to their
  household of residence in each survey year.

  Params:
    filename (str) - CSV to read; must have format described in module comments
    ignore_errors (boolean) - if True, ignore data errors (action on erroneous
      data is undefined); if False, raise ValueError

  Returns:
    a dict with the format
      {id1: {year1: HH_in_year1, year2: ...}, id2: {...} ...}
  """
  hh_memb = {}
  with open(filename) as f:
    reader = csv.DictReader(f)
    for row in reader:
      if all(not val for val in row.values()):
        continue   # ignore blank row
      idnum = int(row['Number'])
      hhs = {
        1986: canonical_hh(row['Hhold N 1986']),
        1992: canonical_hh(row['Hhold 1992']),
        1999: canonical_hh(row['Hhold 1999']),
        2010: canonical_hh(row['Hhold 2010']),
      }
      hh_memb[idnum] = hhs

  return hh_memb


def get_household_wealth_from_file(filename=DEFAULT_HH, ignore_errors=False):
  """
  Parse the MasterSheet file and return a mapping of household names to their
  estimated wealth quartile in each survey year.

  Since the MasterSheet file only contains data by individuals rather than by
  households, wealth quartiles appear for each individual's row (containing all
  survey years).  For individuals in the same household in the same year, these
  quartiles would be identical in theory.  However, due to data errors, they
  are not identical.  To deal with this, we collect all reported wealth
  quartiles for each household-year combination, and take the most frequently
  reported value (the mode) to be the true quartile for that household for that
  year.

  Params:
    filename (str) - CSV to read; must have format described in module comments
    ignore_errors (boolean) - if True, ignore data errors (action on erroneous
      data is undefined); if False, raise ValueError

  Returns:
    a dict with the format
      {
        hh_name_1: {
          year1: {
            'raw_vals': [reported_quartile_1, ...],
            'mode': most_frequently_reported_quartile,
          },
          year2: {...},
          ...
        },
        hh_name_2: {...}, ...
      }
  """
  hh_wealth = {}
  with open(filename) as f:
    reader = csv.DictReader(f)
    for row in reader:
      if all(not val for val in row.values()):
        continue   # ignore blank rows

      # Pull out household names and wealth quartiles
      hh86 = canonical_hh(row['Hhold N 1986'])
      hh92 = canonical_hh(row['Hhold 1992'])
      hh99 = canonical_hh(row['Hhold 1999'])
      hh10 = canonical_hh(row['Hhold 2010'])
      wl86 = row['Wealth 1987']
      wl92 = row['Wealth 1992']
      wl99 = row['Wealth 1999']
      wl10 = row['Wealth 2010']

      # Add reported wealth quartiles to data for that household-year
      hh_wealth.setdefault(hh86, {}).setdefault(1986, {}).setdefault(
        'raw_vals', []).append(wl86)
      hh_wealth.setdefault(hh92, {}).setdefault(1992, {}).setdefault(
        'raw_vals', []).append(wl92)
      hh_wealth.setdefault(hh99, {}).setdefault(1999, {}).setdefault(
        'raw_vals', []).append(wl99)
      hh_wealth.setdefault(hh10, {}).setdefault(2010, {}).setdefault(
        'raw_vals', []).append(wl10)

  # Extract most frequently reported quartile for each household-year
  for hh in hh_wealth.keys():
    for year in hh_wealth[hh].keys():
      raw_vals = hh_wealth[hh][year]['raw_vals']
      if len(set(raw_vals)) == 1:
        # *set* length is 1, all rows reported the same wealth quartile
        hh_wealth[hh][year]['mode'] = raw_vals[0]
      else:
        # multiple quartiles reported, do our best and warn about the error
        counts = {}
        for val in raw_vals: counts[val] = counts.get(val, 0) + 1
        hh_wealth[hh][year]['mode'] = sorted(
          counts.keys(), cmp=lambda a,b: cmp(counts[b], counts[a]))[0]
        print "WARNING: Values for HH %s (%s) vary: %r -- using %s" % (
          hh, year, raw_vals, hh_wealth[hh][year]['mode'])

  return hh_wealth


def households(hh_data):
  """
  Given a household-data dict as input, return a list of household names.

  Params:
    hh_data (dict) - generally the return value of
        get_household_membership_from_file()

  Returns: (list of str) - a sorted list of names of households
  """
  return sorted([i for i in set(
    sum([hh_data[i].values() for i in hh_data.keys()], [])) if i is not None])


def hh_members(hh_data, hh_str, year=None):
  """
  Given a household-data dict, return a list of members of a given household.

  Params:
    hh_data (dict) - generally the return value of
        get_household_membership_from_file()
    hh_str (str) - name of the household we're interested in
    year (int) - if given, return membership for this year; if None, return the
        union of all members throughout the years

  Returns: (list of int) - a sorted list of IDs of the household's members
  """
  if year is None:
    return sorted(i for i in hh_data.keys() if hh_str in hh_data[i].values())
  else:
    return sorted(i for i in hh_data.keys() if hh_str == hh_data[i][year])


def verify_ibp_and_marriages(
      ibpfile=DEFAULT_IBP, marrfile=DEFAULT_MARR, print_errors=True):
  """
  Data-cleaning: Find ID numbers of likely placeholder people.

  At one point, the file was augmented by placeholder people about whom nothing
  was known, e.g. "This person had a father and a mother, of course, but we
  don't know who they are, so we'll create new ID numbers for them but not
  assign any information to those ID numbers."  This was bad data hygiene,
  because the new additions contributed absolutely nothing -- it was more
  sensible to have blank parent IDs in that case.  Besides, don't the new
  placeholder parents need their own placeholder parents?

  This function finds ID numbers of people who are likely to be placeholders.
  """
  ibp = get_ibp_data_from_file(ibpfile, ignore_errors=True)
  i2m, mdata = get_marriage_data_from_file(marrfile, ignore_errors=True)
  errors = []
  removal_candidates = {}

  # Look through the identity records for people who: (1) aren't in the marriage
  # table, and (2) have no information besides their "name" (probably something
  # like "X's Father") and sex.  If they have marriage information or other
  # data, they aren't placeholders.

  for i in ibp:
    if i2m.get(i): continue
    if not any([v for k,v in ibp[i].items() if k not in ("name", "sex")]):
      removal_candidates[i] = 0

  # Next, look through everyone's parents' ID numbers, and count the number of
  # times they appear.  Any parent whose ID appears more than once is necessary:
  # this allows us to determine that two people are brothers, e.g., since they
  # have the same parents.

  for i in ibp:
    fid, mid = ibp[i]["father_id"], ibp[i]["mother_id"]
    if fid in removal_candidates:
      removal_candidates[fid] += 1
    if mid in removal_candidates:
      removal_candidates[mid] += 1
  for i in removal_candidates:
    if removal_candidates[i] < 2:
      errors.append(
        "Removal candidate: %r (%s)" % (ibp[i]["name"], i))

  # Report errors and indicate result (through return value or exception)

  if errors:
    if print_errors:
      print "\n".join(errors)
      return False
    else:
      raise ValueError(errors)
  return True
