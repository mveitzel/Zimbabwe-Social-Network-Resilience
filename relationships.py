#!/usr/bin/python

"""
relationships.py module: functions for computing kinship relationships, as well
as related information like household statistics.

Depends on input parsing functions from genealogy.py module.
"""

import sys, os, re, time
import csv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import genealogy as G


def relationship_name(chain1, style='new'):
  """
  Given two kinship chains from two people to a mutual relative, return the
  English word describing the relationship between the two end people.

  Some of our algorithms to determine relationships start with the two people
  in question and explore outward through the kinship network until a common
  relative is found.  This produces two chains of relatives, one from each
  person to the common relative.  This function takes those chains as input and
  returns the word describing the second person's relationship to the first.

  Parameters:
    chain1 (list of one-element dicts) - has the form
       [{'self': 3}, {'parent': 5001}, {'child': 2}, {'self': 2}, {'spouse': 1}]

       (The second "self" entry is an artifact from merging two chains when
        searching inward from the ends.)

    style (str) - "new" for all live code; old code could use "numeric" to
       return the number of (non-self) links, i.e. consanguinity degree
  """
  relationships = [i.keys()[0] for i in chain1 if i.keys()[0] != 'self']
  if style == 'new':
    raw_result = "'s ".join(relationships)
  elif style == 'numeric':
    return len(relationships)
  else:
    raise ValueError('Invalid style: %r' % style)

  computed = raw_result
  replacements = [
      ("parent's parent's parent's parent's child's child's child's child", "third cousin"),
      ("parent's parent's parent's child's child's child", "second cousin"),
      ("parent's parent's child's child", "first cousin"),
      ("parent's child", "sibling"),
      ("parent's parent's parent's parent", "great-great-grandparent"),
      ("parent's parent's parent", "great-grandparent"),
      ("parent's parent", "grandparent"),
      ("child's child's child's child", "great-great-grandchild"),
      ("child's child's child", "great-grandchild"),
      ("child's child", "grandchild"),
  ]
  for repl in replacements:
    try:
      computed = re.sub(repl[0], repl[1], computed)
    except TypeError:
      print "ERROR: re.sub(%r, %r, %r)" % (repl[0], repl[1], computed)
      raise
  return computed


def generate_connections(anon=True, ignore_errors=True):
  """
  Parse identity and marriage data files, find all first-order connections
  (parent, child, and spouse relationships), and return that data in a
  dictionary mapping ID numbers to dicts of first-order connections.  This is
  our representation of the kinship network.

  Args:
    anon (boolean) - if True, use the anonymized data file (see genealogy.py)
    ignore_errors (boolean) - passed to parsing funcs in genealogy module

  Returns:
     { id1: { id1_fid: 'parent', id1_mid: 'parent', id1_s1id: 'spouse',
              id1_s2id: 'spouse', id1_c1id: 'child', ... },
       id2: { id2_fid: 'parent', ... },
       ... }
  """
  if anon:
    ibp_data = G.get_ibp_data_from_file(
      filename=G.ANON_IBP, ignore_errors=ignore_errors)
  else:
    ibp_data = G.get_ibp_data_from_file(ignore_errors=ignore_errors)
  indivs_to_marriages, marriage_data = G.get_marriage_data_from_file(
    ignore_errors=ignore_errors)

  conns = {}
  for _id in set(ibp_data.keys() + indivs_to_marriages.keys()):
    conns.setdefault(_id, {})
    f_id, m_id, spouse_ids = None, None, []
    if _id not in ibp_data:
      print 'WARNING: ID %d not in ibp_data' % _id
    else:
      f_id = ibp_data[_id].get('father_id')
      m_id = ibp_data[_id].get('mother_id')
    spouse_ids = [ [i for i in id_pair if i != _id][0]
                   for id_pair in indivs_to_marriages.get(_id, [])]
    if f_id is not None:
      conns[_id][f_id] = 'parent'
      conns.setdefault(f_id, {})
      conns[f_id][_id] = 'child'
    if m_id is not None:
      conns[_id][m_id] = 'parent'
      conns.setdefault(m_id, {})
      conns[m_id][_id] = 'child'
    for s_id in spouse_ids:
      conns[_id][s_id] = 'spouse'
      conns.setdefault(s_id, {})
      conns[s_id][_id] = 'spouse'

  return conns


def invert_chain(chain):
  """
  Given a chain of kinship describing A's relationship to B, return the inverted
  chain describing B's relationship to A.

  Parameters:
    chain (list of str) - has the form
       [{'self': 1}, {'parent': 111}, {'child': 222}, {'spouse': 333}, ...]
       (for this example, the chain represents a sibling-in-law)

  Returns:
    (list of str) - the inverted chain; in the example above, it would be
       [{'self': 333}, {'spouse': 222}, {'parent': 111}, {'child': 1}]
  """
  inverses = {'parent': 'child', 'spouse': 'spouse', 'child': 'parent',
              'self': 'self'}
  result, next_rel = [], 'self'
  for link in reversed(chain):
    this_rel, this_id = link.items()[0]
    result.append({inverses[next_rel]: this_id})
    next_rel = this_rel
  return result


def find_relationship(id1, id2, conns, max_links=None, debug=False):
  """
  Return the kinship relation, if any, between id1 and id2.

  Algorithm:
    Breadth-first search of all relatives, starting with id1 and id2.  This
    works inward from both ends, generally minimizing the graph space explored.
    It also automatically enforces ordering by kinship distance.  When a
    relative of id1 is found who is also a relative of id2 (or vice versa), we
    have both proven that id1 and id2 are related, and found the shortest path
    between them.

    Note that in the case of multiple relationships (e.g. double cousins, who
    may be first cousins on one side and third cousins on the other), only the
    closest relationship ("first cousin" in this case) is returned.

  Args:
    id1, id2 (int) - ID numbers of people to find a kinship relation between
    conns (dict) - return value of generate_connections(), i.e. kinship network
    max_links (int or None) - if given, return None if no kinship relation can
       be found within this many links
    debug (boolean) - passed to relationship_name()

  Returns:
    (None) if no kinship relation can be found (or if max_links is exceeded)
    (str) The name of id2's relation to id1, e.g. "grandparent" if id2 is id1's
    grandparent.  Relationship names are limited to the return values of the
    relationship_name() function.
  """
  if id1 == id2: return "self"

  if id1 not in conns: raise ValueError('"%s" not in data' % id1)
  if id2 not in conns: raise ValueError('"%s" not in data' % id2)

  known1 = {id1: [{'self': id1}]}
  known2 = {id2: [{'self': id2}]}

  to_explore = [id1, id2]
  ids_seen = []
  known_chain = None

  while to_explore:
    new_rel, to_explore = to_explore[0], to_explore[1:]

    # We're working inward from both id1 and id2 -- which one have we
    # determined is a relative of new_rel?  Assign my_rels and target_rels
    # appropriately.
    my_rels = (known1 if new_rel in known1 else known2)
    target_rels = (known2 if new_rel in known1 else known1)

    if (max_links is not None and len(my_rels[new_rel]) > max_links):
      # with max_links=1, my_rels[new_rel] maxes out at [self, relative]
      # with max_links=2, [self, relative, relative], etc.
      continue

    new_rel_link_dict = conns[new_rel]
    for conn_id, conn_name in new_rel_link_dict.items():
      # id1 is related to conn_id!  If this is news, then store the new relative
      new_path = my_rels[new_rel] + [{conn_name: conn_id}]
      if conn_id not in my_rels or len(new_path) < len(my_rels[conn_id]):
        my_rels[conn_id] = new_path

      # If conn_id is related to id2, then id1 and id2 are related
      if conn_id in target_rels:
        if (known_chain is None or
            len(known_chain) > len(known1[conn_id]) + len(known2[conn_id])):
          known_chain = known1[conn_id] + invert_chain(known2[conn_id])

      if conn_id not in ids_seen:
        to_explore.append(conn_id)

      ids_seen.append(conn_id)

  if known_chain:
    chain_length = sum(len(ch) for ch in known_chain) - 2
    if max_links is None or chain_length <= max_links:
      return relationship_name(known_chain, style='new')

  return None


def old_print_all_relationships(
    output_to="/tmp/kinship-%02d-links.csv", ignore_errors=True, anon=True,
    max_links=10):
  """
  Old function (no longer used, but potentially useful in future research)
  to output all relationships which are no more than max_links apart.

  Args:
    output_to (str) - parameterized filename (must contain one formatting param
       such as "%d") describing how to store the output for each max-link-count
    ignore_errors (boolean) - passed to input file parsers in genealogy module
    anon (boolean) - if True, use the anonymized data file (see genealogy.py)
    max_links (int) - write output files for 1 link, 1-or-2 links, 1-to-3
       links, ... 1-to-max_links links

  Actions:
    creates up to max_links CSV output files using output_to as the filename
    template; CSV file contents can easily be customized, currently set to
    "A's ID", "B's ID", "A's relationship to B", "B's relationship to A"

  Returns: None
  """

  conns = generate_connections(anon=anon, ignore_errors=ignore_errors)
  if anon:
    ibp_data = G.get_ibp_data_from_file(
      filename=G.ANON_IBP, ignore_errors=ignore_errors)
  else:
    ibp_data = G.get_ibp_data_from_file(ignore_errors=ignore_errors)

  id_list = sorted(conns.keys())
  inverses = {'parent': 'child', 'spouse': 'spouse', 'child': 'parent'}

  reln_links = {i: {} for i in id_list}
  for n_links in range(1, max_links+1):
    with open(output_to % n_links, "w") as f:
      if n_links == 1:
        for _id in id_list:
          reln_links[_id] = {k: [v] for k, v in conns[_id].items()}
      else:
        for _id in reln_links:
          all_rels = reln_links[_id].keys()
          last_rels = [r for r in all_rels
                       if len(reln_links[_id][r]) == n_links - 1]
          for last_link in last_rels:
            for next_link_id, next_link_name in conns[last_link].items():
              if next_link_id in reln_links[_id]: continue
              reln_links[_id][next_link_id] = (
                reln_links[_id][last_link] + [next_link_name])
              reln_links[next_link_id][_id] = (
                [inverses[next_link_name]] + reln_links[last_link][_id])

      f.write('"A\'s ID","B\'s ID","B is A\'s","A is B\'s"\n')
      #f.write('"A\'s ID","B\'s ID","Distance from A to B"\n')
      for index1 in range(len(id_list)):
        id1 = id_list[index1]
        for id2 in id_list[index1+1:]:
          if id1 in reln_links[id2] and id2 not in reln_links[id1]:
            raise ValueError("%s in %s but not vice versa" % (id1, id2))
          if id2 in reln_links[id1] and id1 not in reln_links[id2]:
            raise ValueError("%s in %s but not vice versa" % (id2, id1))
          if id2 not in reln_links[id1]:
            # continue
            f.write('%d,%d,"%s","%s"\n' % (id1, id2, '', ''))
          else:
            # each in the other's map, so print 'em
            rel1 = relationship_name(reln_links[id1][id2], style='new')
            rel2 = relationship_name(reln_links[id2][id1], style='new')
            f.write('%d,%d,"%s","%s"\n' % (id1, id2, rel1, rel2))


def find_all_relationships(
    output_to="/tmp/kinship-distances.csv", ignore_errors=True, anon=True):
  """
  Generate all connections in the kinship graph using Floyd-Warshall, write
  the information to a file, and return the minimum-distance table and
  shortest-path tree.

  This supersedes the old function old_print_all_relationships(), which is only
  retained to verify that its results match this function's results.

  Args:
    output_to (str) - parameterized filename (must contain one formatting param
       such as "%d") describing how to store the output for each max-link-count
    ignore_errors (boolean) - passed to input file parsers in genealogy module
    anon (boolean) - if True, use the anonymized data file (see genealogy.py)

  Returns:
    pair_paths, short_path_tree
      pair_paths (dict): table of distances between all IDs such that
           pair_paths[id1][id2] = min number of links between ID1 and ID2
      short_path_tree (dict): table of "which node do I go to next?" for use
        with the path() function, which can regenerate the shortest path
  """

  conns = generate_connections(anon=anon, ignore_errors=ignore_errors)
  if anon:
    ibp_data = G.get_ibp_data_from_file(
      filename=G.ANON_IBP, ignore_errors=ignore_errors)
  else:
    ibp_data = G.get_ibp_data_from_file(ignore_errors=ignore_errors)

  id_list = sorted(conns.keys())

  # Floyd-Warshall algorithm for all-pairs-shortest-path
  # Use edge list to initialize shortest-path tree and all-pairs lengths
  sys.stderr.write('   [%s] Starting Floyd-Warshall...\n' % time.ctime())
  pair_paths = {}
  short_path_tree = {}
  NO_CONN = 9e9   # indicates no connection between these two nodes
  for i in id_list:
    pair_paths[i] = {}
    short_path_tree[i] = {}
    for j in conns[i].keys():
      pair_paths[i][j] = 1
      short_path_tree[i][j] = j
  # Try to find a shorter path by seeing if an intermediate node will help
  for new_intermediate in id_list:
    for person1 in id_list:
      for person2 in id_list:
        if (pair_paths[person1].get(new_intermediate, NO_CONN) +
            pair_paths[new_intermediate].get(person2, NO_CONN) <
            pair_paths[person1].get(person2, NO_CONN)):
          pair_paths[person1][person2] = (
            pair_paths[person1][new_intermediate] +
            pair_paths[new_intermediate][person2])
          short_path_tree[person1][person2] = (
            short_path_tree[person1][new_intermediate])
  sys.stderr.write('   [%s] Finished\n' % time.ctime())

  with open(output_to, "w") as f:
    f.write('"A\'s ID","B\'s ID","Distance from A to B"\n')
    for index1 in range(len(id_list)):
      id1 = id_list[index1]
      for id2 in id_list[index1+1:]:
        if id1 in pair_paths[id2] and id2 not in pair_paths[id1]:
          raise ValueError("%s in %s but not vice versa" % (id1, id2))
        if id2 in pair_paths[id1] and id1 not in pair_paths[id2]:
          raise ValueError("%s in %s but not vice versa" % (id2, id1))
        if id2 not in pair_paths[id1]:
          f.write('%d,%d,"%s"\n' % (id1, id2, ''))
          continue
        if pair_paths[id1][id2] != pair_paths[id2][id1]:
          raise ValueError("Dist from %s to %s (%s) != dist from %s to %s (%s)"
                           % (id1, id2, pair_paths[id1][id2],
                              id2, id1, pair_paths[id2][id1]))

        f.write('%d,%d,%d\n' % (id1, id2, pair_paths[id1][id2]))

  return pair_paths, short_path_tree


def path(tree, id1, id2):
  """
  Given a shortest-path tree returned by find_all_relationships() and the IDs
  of two people, return the shortest path through the kinship network to get
  from ID1 to ID2.

  Args:
    tree (dict) - table of "which node do I go to next?" which can be used to
       reconstruct the shortest path between any two nodes:
           tree[id1][id2] = someone directly related to ID1 who is the best
                            next link to get you to ID2
    id1, id2 (int) - IDs that we're trying to link

  Returns:
    empty list if id1 and id2 are unrelated
    [id1, id1_rel, ..., id2] if there is a path from ID1 to ID2
  """
  if tree[id1].get(id2, None) is None:
    return []
  mypath = [id1]
  link = id1
  while link != id2:
    link = tree[link][id2]
    mypath.append(link)
  return mypath


def household_stats(outfilename):
  """
  Read household membership data, compute stats for each HH for each year,
  write results as CSV to outfile, and return results as a dict.

  Args:
    outfilename (str) - name of CSV file to write
       headers are "Household ID", "Year", "Size", "Median Dist", "Wealth"

  Returns:
    (dict) {
       hh_id: {
         year1: {
           statname1: value, statname2: value, ...
         },
         year2: { ...},
       }, hh2_id: {...}, ...
     }
  """
  conns = generate_connections()
  hh_data = G.get_household_membership_from_file()
  hh_names = G.households(hh_data)
  years = (1986, 1992, 1999, 2010)
  wealth = G.get_household_wealth_from_file()
  results = {hh: {y: {} for y in years} for hh in hh_names}
  for hh in hh_names:
    for year in years:
      members = G.hh_members(hh_data, hh, year)
      if not members: continue
      results[hh][year]['size'] = len(members)
      results[hh][year]['_members'] = members
      results[hh][year]['wealth'] = wealth[hh][year]['mode']
      dists = []
      for i1 in range(len(members)):
        id1 = members[i1]
        if id1 not in conns:
          print "WARNING: Bad ID: %s [HH %s, %s]" % (id1, hh, year)
          continue
        for i2 in range(i1+1, len(members)):
          id2 = members[i2]
          if id2 not in conns:
            print "WARNING: Bad ID: %s [HH %s, %s]" % (id2, hh, year)
            continue
          dists.append(find_relationship(id1, id2, conns))
      results[hh][year]['_dists'] = dists
      if len(members) == 1:
        results[hh][year]['median_dist'] = None
        continue
      if not dists:
        print "ERROR: members = %r, dists = %r" % (members, dists)
        raise ValueError("No dists for HH %s year %s" % (hh, year))
      if len(dists) % 2 == 1:
        results[hh][year]['median_dist'] = dists[len(dists)/2]
      else:
        results[hh][year]['median_dist'] = (
          dists[len(dists)/2 - 1] + dists[len(dists)/2]) / 2.0

  with open(outfilename, "w") as f:
    f.write('"Household ID","Year","Size","Median Dist","Wealth"\n')
    for hh in hh_names:
      for year in years:
        data = results[hh][year]
        if not data: continue
        if not data.get('median_dist'):
          print 'WARNING: No median_dist for HH %s in %d' % (hh, year)
          continue
        f.write('"%s",%d,%d,%.1f,"%s"\n' % (
          hh, year, data['size'], data['median_dist'], data['wealth']))

  return results


def year_for(yearstr):
  """
  Return best guess of the year as an integer.  (Cleans up messy source data.)

  Args:
    yearstr (str) - a year from the original (messy) source data

  Returns: int
  """
  try:
    return int(yearstr)
  except ValueError:
    if yearstr == '2000s': return 2005
    raise


def hh_change(hh_data, hh):
  """
  Print summary information about a household's change over the years.

  Args:
    hh_data (dict) - return value of household_stats()
    hh (str) - name of household to output information about; must be in the
       list returned by genealogy modules households() function

  Returns: None
  """
  print "=== Household %s ===" % hh
  ibp = G.get_ibp_data_from_file(ignore_errors=True)
  ibp[3989] = {'birthyear': '1987'}
  years = (1986, 1992, 1999, 2010)
  members_sets = [set(G.hh_members(hh_data, hh, y)) for y in years]
  for i, memb_set in enumerate(members_sets):
    print "%s: %r" % (years[i], list(memb_set))
  if not any(members_sets[:-1]):
    print ("Household %s did not exist before last survey -- "
           "no deltas can be computed" % hh)
    return

  for i in range(1, len(years)):
    oldset, newset = members_sets[i-1], members_sets[i]
    if not oldset:
      print "%d: Household %s did not exist" % (years[i-1], hh)
      continue
    dist = len(newset - oldset) + len(oldset - newset)
    print ("  %s to %s\n    orig size: %d\n    distance from previous: %d\n  "
           "    change from previous: %.1f%%") % (
             years[i-1], years[i], len(oldset), dist,
             100.0*dist/len(oldset) if oldset else 100)
    b_list, d_list, i_list, e_list = [], [], [], []
    for newid in sorted(list(newset - oldset)):
      if not ibp[newid]['birthyear']:
        print 'WARNING: Unknown birth year for ID %d' % newid
      elif years[i-1] > year_for(ibp[newid]['birthyear']):
        i_list.append(str(newid))
      else:
        b_list.append(str(newid))
    for oldid in sorted(list(oldset - newset)):
      if (not ibp[oldid]['best_dod'] or
          year_for(ibp[oldid]['best_dod']) > years[i]):
        e_list.append(str(oldid))
      else:
        d_list.append(str(oldid))
    print "            born: + %d (%s)" % (len(b_list), ', '.join(b_list))
    print "      immigrated: + %d (%s)" % (len(i_list), ', '.join(i_list))
    print "       emigrated: - %d (%s)" % (len(e_list), ', '.join(e_list))
    print "            died: - %d (%s)" % (len(d_list), ', '.join(d_list))


def hh_years_of_existence(hh_data):
  """
  Print summary information about which households came into existence or
  became defunct in each survey year.

  Args:
    hh_data (dict) - return value of household_stats()
  """
  years = (1986, 1992, 1999, 2010)
  hhnames = G.households(hh_data)
  hhyears = {
    hh: [y for y in years if G.hh_members(hh_data, hh, y)] for hh in hhnames
  }
  hh_sets_by_year = {
    y: set([hhname for hhname in hhyears if y in hhyears[hhname]])
    for y in years
  }
  print "Year %d: [baseline]" % years[0]
  for index in range(1, len(years)):
    this_y, last_y = years[index], years[index-1]
    print "Year %d:" % this_y
    print "  New households: %s" % (
      sorted(hh_sets_by_year[this_y] - hh_sets_by_year[last_y]))
    print "  Defunct households: %s" % (
      sorted(hh_sets_by_year[last_y] - hh_sets_by_year[this_y]))


def subset_alive_in(ibp, year, id_list):
  """
  Return the subset of id_list which are IDs of people who were alive in year.
  """
  # TODO: THIS DOES NOT WORK.  Some people in households are related to people
  # not in households.  Some of those semi-tracked people don't have a DOB or
  # DOD in the IBP data.  So we really can't tell whether they're historical
  # figures or contemporary auxiliary people -- and therefore we don't know
  # whether they're alive or not.  An example is ID 5143.
  try:
    return [i for i in id_list if year_for(ibp[i]['birthyear'] or ibp[i]['best_dod']) <= year and
            year_for(ibp[i]['best_dod'] or 9999) >= year]
  except ValueError:
    print "ERROR: year=%d, id_list=%s" % (year, id_list)
    print "; ".join(["%s: %r-%r" % (i, (ibp[i]['birthyear'] or ibp[i]['best_dod']), ibp[i]['best_dod'] or 9999) for i in id_list])


def hh_head_in_year(hh_number, year):
  """
  Return the ID of the household head for the given household in the given year.
  """
  hh_heads = {
    '1':   {1986: 1,    1992: 2,    1999: 2,    2010: 2},
    '1.1': {1986: None, 1992: None, 1999: None, 2010: 3068},
    '1.2': {1986: None, 1992: None, 1999: None, 2010: 4},
    '2':   {1986: 21,   1992: 21,   1999: 21,   2010: 21},
    '3':   {1986: 31,   1992: 31,   1999: 31,   2010: 31},
    '3.1': {1986: None, 1992: None, 1999: None, 2010: 34},
    '3.2': {1986: None, 1992: None, 1999: None, 2010: 3021},
    '3.3': {1986: None, 1992: None, 1999: None, 2010: 3073},
    '3.4': {1986: None, 1992: None, 1999: None, 2010: 894},
    '4':   {1986: 38,   1992: 38,   1999: 39,   2010: 39},
    '4.1': {1986: None, 1992: 40,   1999: 40,   2010: 40},
    '4.2': {1986: None, 1992: None, 1999: None, 2010: 45},
    '5':   {1986: 48,   1992: 48,   1999: 54,   2010: 54},
    '5.1': {1986: None, 1992: None, 1999: 48,   2010: 48},
    '5.2': {1986: None, 1992: 58,   1999: 59,   2010: 59},
    '5.3': {1986: None, 1992: None, 1999: None, 2010: 3059},
    '6':   {1986: 64,   1992: 64,   1999: 64,   2010: 3060},
    '6.1': {1986: None, 1992: None, 1999: None, 2010: 71},
    '6.2': {1986: None, 1992: None, 1999: None, 2010: 68},
    '6.4': {1986: None, 1992: None, 1999: None, 2010: 65},
    '6.5': {1986: None, 1992: None, 1999: None, 2010: 74},
    '6.6': {1986: None, 1992: None, 1999: None, 2010: 66}
  }
  if hh_number not in hh_heads:
    raise ValueError("Unrecognized household: %r" % hh_number)
  if year not in hh_heads[hh_number]:
    raise ValueError("Unrecognized year: %r" % year)
  return hh_heads[hh_number][year]


def degree_distribution(anon=True):
  """
  Return a dict mapping a degree (a count of relatives) to the number of people
  who have that degree.
  """

  #years = (1986, 1992, 1999, 2010)
  years = (2010,)
  conns = generate_connections(anon=anon, ignore_errors=True)
  ibp = G.get_ibp_data_from_file(ignore_errors=True)
  hh_data = G.get_household_membership_from_file()
  bad_households = ('66', '14', '6.7', '1.2', '3.4')  # not in analysis
  hh_names = [hh for hh in G.households(hh_data) if hh not in bad_households]

  for year in years:
    degrees = {}
    hh_head_degrees = {}
    for hh in hh_names:
      for hh_member in G.hh_members(hh_data, hh, year):
        if hh_member == 3989: continue  # ERROR: not in IBP or IndivsToMarriages
        # TODO: Commenting this out uses the kinship graph at the most recent
        # sample when calculating the node degree.
        #
        #living_relatives = subset_alive_in(ibp, year, conns[hh_member])
        #degree = len(living_relatives)
        living_and_nonliving_relatives = conns[hh_member]
        degree = len(living_and_nonliving_relatives)
        #degrees[degree] = degrees.get(degree, 0) + 1
        degrees.setdefault(degree, []).append(hh_member)
        if hh_head_in_year(hh, year) == hh_member:
          hh_head_degrees[degree] = hh_head_degrees.get(degree, 0) + 1
    print "Year: %d" % year
    print "Overall degree distribution: %s" % {count: who for count, who in degrees.items() if count >= 9}
    print "Household-head degree distribution: %s" % hh_head_degrees


def write_hh_degree_info(outfile, anon=True):
  """
  For each member of each household, output the following to CSV:
    ID, Household, Degree, Household Head (TRUE/FALSE), Gender (M/F)

  Note that the degree given will be the total number of edges to any relatives,
  living or dead.

  Args:
    outfile (str) - name of CSV file to write results to
  """

  conns = generate_connections(anon=anon, ignore_errors=True)
  ibp = G.get_ibp_data_from_file(ignore_errors=True)
  hh_data = G.get_household_membership_from_file()
  bad_households = ('66', '14', '6.7', '12.2')  # not in analysis
  hh_names = [hh for hh in G.households(hh_data) if hh not in bad_households]

  year = 2010
  all_years = (1986, 1992, 1999, 2010)
  degrees = {}
  hh_head_degrees = {}
  with open(outfile, "w") as f:
    f.write('"ID","Household","Degree","IsHouseholdHead","Gender"\n')
    for hh in hh_names:
      for hh_member in G.hh_members(hh_data, hh, year):
        if hh_member == 3989: continue  # ERROR: not in IBP or IndivsToMarriages
        living_and_nonliving_relatives = conns[hh_member]
        degree = len(living_and_nonliving_relatives)
        is_hh_head = any([(hh_member == hh_head_in_year(hh, y)) for y in all_years])
        f.write('%d,"%s",%d,%s,"%s"\n' % (
          hh_member, hh, degree, str(is_hh_head).upper(), ibp[hh_member]['sex']))


def min_and_max_household_degrees(outfilename, anon=True, pair_paths=None):
  """
  For each household in each year, find the maximum finite kinship degree in that
  household, and also find any people in the household who are unrelated to the
  rest of the household.
  """
  all_years = (1986, 1992, 1999, 2010)
  if pair_paths is None:
    pair_paths, _ = find_all_relationships(anon=anon)
  hh_data = G.get_household_membership_from_file()
  bad_households = ('66', '14', '6.7', '1.2', '3.4', '12.2')  # not in analysis
  hh_names = [hh for hh in G.households(hh_data) if hh not in bad_households]
  with open(outfilename, 'w') as f:
    f.write('"Household","Year","Node Count","Max Finite Kinship Dist"\n')
    for year in all_years:
      for hh in hh_names:
        hh_members = G.hh_members(hh_data, hh, year)
        if not hh_members: continue
        max_finite_dist_for_hh = None
        min_dist_seen_already = {}
        for index, hh_member_id in enumerate(hh_members[:-1]):
          min_dist_for_member = None
          for counterpart_index in range(index+1, len(hh_members)):
            counterpart_id = hh_members[counterpart_index]
            dist = pair_paths[hh_member_id].get(counterpart_id)
            if dist is not None:
              if (min_dist_seen_already.get(counterpart_id) is None or
                  min_dist_seen_already.get(counterpart_id) > dist):
                min_dist_seen_already[counterpart_id] = dist
              if min_dist_for_member is None or min_dist_for_member > dist:
                min_dist_for_member = dist
              if max_finite_dist_for_hh is None or max_finite_dist_for_hh < dist:
                max_finite_dist_for_hh = dist
          if (min_dist_for_member is None and
              min_dist_seen_already.get(hh_member_id) is None):
            print "HH %-3s in %s: ID %s is not related" % (hh, year, hh_member_id)
        print "HH %-3s in %s: %2d nodes, max finite kinship distance is %s" % (
          hh, year, len(hh_members), max_finite_dist_for_hh)
        f.write('"%s",%d,%d,%d\n' % (hh, year, len(hh_members),
                                     max_finite_dist_for_hh))
