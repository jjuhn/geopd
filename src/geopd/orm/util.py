from geopd import config
from geopd.orm.db import *

import csv
import dateutil.parser
import pkg_resources
import os.path
import Bio.Entrez


########################################################################################################################
# Initialize Operational Database
########################################################################################################################


def init_db():

    Base.metadata.drop_all(db.bind)
    Base.metadata.create_all(db.bind)

    db.add(UserStatus(USER_STATUS_PENDING, 'Pending'))
    db.add(UserStatus(USER_STATUS_ACTIVE, 'Active'))
    db.add(UserStatus(USER_STATUS_DISABLED, 'Disabled'))

    institutions = dict()
    institutions_stream = pkg_resources.resource_stream('geopd.orm', os.path.join('data', 'institutions.tsv'))
    for row in csv.DictReader(institutions_stream, delimiter='\t'):
        institution = Institution(row['name'], city=row['city'], latitude=row['latitude'], longitude=row['longitude'])
        institutions[row['name']] = institution
        db.add(institution)

    members = dict()
    members_stream = pkg_resources.resource_stream('geopd.orm', os.path.join('data', 'members.tsv'))
    for row in csv.DictReader(members_stream, delimiter='\t'):
        member = User(row['email'], config.get('db.init', 'password'), row['name'])
        member.institution = institutions[row['institution']]
        member.status_id = USER_STATUS_ACTIVE
        member.confirmed = True
        member.force_password_reset = True
        members[row['name']] = member
        db.add(member)
        db.flush()
        member.info = UserInfo(member.id)

    clinical_stream = pkg_resources.resource_stream('geopd.orm', os.path.join('data', 'clinical.tsv'))
    for row in csv.DictReader(clinical_stream, delimiter='\t'):
        clinical = ClinicalInfo(row['name'])
        db.add(clinical)

    epidemiologic_stream = pkg_resources.resource_stream('geopd.orm', os.path.join('data', 'epidemiologic.tsv'))
    for row in csv.DictReader(epidemiologic_stream, delimiter='\t'):
        epidemiologic = EpidemiologicInfo(row['name'])
        db.add(epidemiologic)

    biospecimen_stream = pkg_resources.resource_stream('geopd.orm', os.path.join('data', 'biospecimen.tsv'))
    for row in csv.DictReader(biospecimen_stream, delimiter='\t'):
        biospecimen = BiospecimenInfo(row['name'])
        db.add(biospecimen)

    projects_stream = pkg_resources.resource_stream('geopd.orm', os.path.join('data', 'projects.tsv'))
    for row in csv.DictReader(projects_stream, delimiter='\t'):
        project = Project(row['name'], row['description'])
        for name in row['investigators'].split(','):
            project.investigators.append(members[name])
        db.add(project)

    publications = dict()
    publications_stream = pkg_resources.resource_stream('geopd.orm', os.path.join('data', 'publications.tsv'))
    for row in csv.DictReader(publications_stream, delimiter='\t'):
        publications[row['pubmed']] = None

    Bio.Entrez.email = 'ozabaneh@can.ubc.ca'
    Bio.Entrez.tool = 'geopd.orm.util'
    handle = Bio.Entrez.esummary(db='pubmed', id=','.join(publications.keys()))
    for rec in Bio.Entrez.read(handle):
        publication = Publication(rec['Id'], rec['Title'])
        publication.source = rec['FullJournalName']
        publication.volume = rec['Volume']
        publication.issue = rec['Issue']
        publication.pages = rec['Pages']
        publication.authors = ','.join(rec['AuthorList'])
        publication.published_on = dateutil.parser.parse(rec['PubDate'])
        publication.epublished_on = dateutil.parser.parse(rec['EPubDate']) if rec['EPubDate'] else None
        publications[rec['Id']] = publication
        db.add(publication)

    handle = Bio.Entrez.efetch(db='pubmed', id=','.join(publications.keys()), rettype='abstract', retmode='xml')
    for rec in Bio.Entrez.read(handle):
        abstract_lines = []
        if 'Abstract' in rec['MedlineCitation']['Article']:
            for s in rec['MedlineCitation']['Article']['Abstract']['AbstractText']:
                abstract_lines.append(s)
            publications[rec['MedlineCitation']['PMID']].abstract = '\n'.join(abstract_lines)

    db.add(Meeting('Paris', 2005, carousel=True))
    db.add(Meeting('Santorini', 2006, carousel=True))
    db.add(Meeting('Trondheim', 2008, carousel=True))
    db.add(Meeting('Tubingen', 2009, carousel=True))
    db.add(Meeting('Toronto', 2010, carousel=True))
    db.add(Meeting('Evanston', 2011, program=True, carousel=True))
    db.add(Meeting('Seoul', 2012, program=True, carousel=True))
    db.add(Meeting('Luebeck', 2013, program=True, carousel=True))
    db.add(Meeting('Vancouver', 2014, program=True, carousel=True))
    db.add(Meeting('Tokyo', 2015, program=True, carousel=True))
    db.add(Meeting('Luxembourg', 2016, program=True))

    db.add(Core('Bioinformatics'))
    db.add(Core('Biology'))
    db.add(Core('Clinical'))
    db.add(Core('Communications'))
    db.add(Core('Epidemiology & Statistics'))

    db.commit()

