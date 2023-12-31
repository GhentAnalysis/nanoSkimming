#!/usr/bin/env python

# imports
import os, sys
import argparse
import ROOT
ROOT.PyConfig.IgnoreCommandLineOptions = True # (?)

# import tools from NanoAODTools
from PhysicsTools.NanoAODTools.postprocessing.framework.postprocessor import PostProcessor
from PhysicsTools.NanoAODTools.postprocessing.framework.crabhelper import inputFiles
import PhysicsTools.NanoAODTools.postprocessing.modules.jme.jetmetHelperRun2 as jme

# import local tools
from PhysicsTools.nanoSkimming.skimselection.multilightleptonskimmer import MultiLightLeptonSkimmer
from PhysicsTools.nanoSkimming.skimselection.nlightleptonskimmer import nLightLeptonSkimmer
from PhysicsTools.nanoSkimming.processing.leptonvariables import LeptonVariablesModule
from PhysicsTools.nanoSkimming.processing.topleptonmva import TopLeptonMvaModule
from PhysicsTools.nanoSkimming.processing.leptongenvariables import LeptonGenVariablesModule
from PhysicsTools.nanoSkimming.processing.triggervariables import TriggerVariablesModule
from PhysicsTools.nanoSkimming.tools.sampletools import getsampleparams


# read command line arguments
parser = argparse.ArgumentParser(description='Submit via CRAB')
parser.add_argument('-n', '--nentries', default=-1, type=int)
args = parser.parse_args()

# print arguments
print('Running with following configuration:')
for arg in vars(args):
    print('  - {}: {}'.format(arg,getattr(args,arg)))

# set input files and output directory
inputfiles = inputFiles()
# (this takes care of file providing via CRAB;
#  when testing locally, this function retrieves the input file defined in PSet.py)
outputdir = '.'
# (must be set to current directory for CRAB jobs to run properly;
#  the actual correct output directory is managed by CRAB)

# get sample parameters
# (note: no check is done on consistency between samples,
#  only first sample is used)
sampleparams = getsampleparams(inputfiles[0])
year = sampleparams['year']
dtype = sampleparams['dtype']
print('Sample is found to be {} {}.'.format(year,dtype))

# set other parameters
jobreport = True
# (must be set to True for CRAB submission,
# else the jobs seem to fail with error codes pointing to missing job reports)
haddname = 'skimmed.root'
# (must be specified if jobreport is True,
# else there are warnings and unconvenient default values;
# note that it must correspond to the value in PSet.py and crabconfig.py.)
provenance = True
# (seems to take care of copying the MetaData and ParameterSets trees)

# define json preskim
jsonfile = None
if dtype=='data':
    jsonfile = '../data/lumijsons/lumijson_{}.json'.format(year)
    if not os.path.exists(jsonfile):
        # for CRAB submission, the data directory is copied to the working directory
        jsonfile = 'data/lumijsons/lumijson_{}.json'.format(year)
    if not os.path.exists(jsonfile):
        raise Exception('ERROR: json file not found.')

# define branches to drop and keep
dropbranches = '../data/dropbranches/default.txt'
if not os.path.exists(dropbranches):
    # for CRAB submission, the data directory is copied to the working directory
    dropbranches = 'data/dropbranches/default.txt'
if not os.path.exists(dropbranches):
    raise Exception('ERROR: dropbranches file not found.')

# set up JetMET module
yeardict = {
  '2016PreVFP': 'UL2016_preVFP',
  '2016PostVFP': 'UL2016',
  '2017': 'UL2017',
  '2018': 'UL2018'
}
JetMetCorrector = jme.createJMECorrector(
  isMC=(dtype=='sim'),
  dataYear=yeardict[year],
  jesUncert="Merged",
  splitJER=False
)

# define modules
leptonmodule = None
if dtype=='data':
    leptonmodule = nLightLeptonSkimmer(2,
      electron_selection_id='run2ul_loose',
      muon_selection_id='run2ul_loose')
else:
    leptonmodule = MultiLightLeptonSkimmer(
      electron_selection_id='run2ul_loose',
      muon_selection_id='run2ul_loose')
modules = ([
  leptonmodule,
  LeptonVariablesModule(),
  TopLeptonMvaModule(year, 'ULv1'),
  TriggerVariablesModule(year),
  JetMetCorrector()
])
if dtype!='data': modules.append(LeptonGenVariablesModule())

# define a PostProcessor
p = PostProcessor(
  outputdir,
  inputfiles,
  modules = modules,
  maxEntries = None if args.nentries<=0 else args.nentries,
  branchsel = dropbranches,
  fwkJobReport = jobreport,
  haddFileName = haddname,
  provenance = provenance,
  jsonInput = jsonfile
)

# run the PostProcessor
p.run()
