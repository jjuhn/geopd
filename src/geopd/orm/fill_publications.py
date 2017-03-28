import Bio.Entrez
from geopd.orm.model import *
import dateutil.parser
import sqlalchemy


PMID = [25003242,
        23124679,
        9887334,
        23744550,
        19139307,
        15451224,
        18824390,
        20013014,
        8285594,
        26350119,
        9705138,
        15451225,
        20818659,
        9276199,
        21656851,
        16358335,
        18195271,
        14755720,
        10867800,
        19562770,
        26635992,
        15760766,
        18571778,
        9629847,
        22410449,
        18413475,
        17251522,
        18852445,
        18852448,
        18852449,
        19405094,
        13915636,
        21412942,
        26880146,
        23441980,
        21761143,
        23674458,
        26749150,
        20222138,
        23283657,
        17625105,
        14593171,
        19833540]




def main():
    # print db.session.query(CorePostComment).all()

    print db.session.query(Project)


    # path = '/Users/jj/private/geopd/data/projects/6/pedigrees/'
    # for f in os.listdir(path):
    #     if os.path.isfile(os.path.join(path, f)):
    #         filename =  f.split(".")[0]
    #         print filename
    #         cp = ContentPedigree(f)
    #
    #         print filename.split("SNCA")[0]
    #         print filename.split("SNCA")[1]
    #         cp.country_code = filename.split("SNCA")[0]
    #         cp.category_id = 6
    #         cp.display_name = filename
    #         cp.pedigree_type = "Progeny Pedigree"
    #
    #         db.session.add(cp)
    #
    #         db.session.flush()
    #         db.session.commit()



    # Bio.Entrez.email = 'ozabaneh@can.ubc.ca'
    # Bio.Entrez.tool = 'geopd.orm.util'
    # handle = Bio.Entrez.esummary(db='pubmed', id=",".join(str(x) for x in PMID))
    # for rec in Bio.Entrez.read(handle):
    #     publication = ContentPublication(rec['Title'])
    #     publication.pmid = rec['Id']
    #     publication.source = rec['FullJournalName']
    #     publication.volume = rec['Volume']
    #     publication.issue = rec['Issue']
    #     publication.pages = rec['Pages']
    #     publication.authors = ','.join(rec['AuthorList'])
    #     publication.published_on = dateutil.parser.parse(rec['PubDate'].split("-")[0])
    #     publication.epublished_on = dateutil.parser.parse(rec['EPubDate']) if rec['EPubDate'] else None
    #     publication.category_id = 5
    #
    #     db.session.add(publication)
    #
    # db.session.flush()
    #
    #
    # db.session.commit()
    # print len(PMID)
    # path = "/Users/jj/private/geopd/data/projects/6/papers/"
    #
    # all_files = []
    # for f in os.listdir(path):
    #     if os.path.isfile(os.path.join(path, f)):
    #         year = f.split("_")[0]
    #         name = f.split("_")[1]
    #
    #         print ContentPublication.query\
    #             .filter(sqlalchemy.extract('year', ContentPublication.published_on)==year)\
    #             .all()
    #             # .filter(ContentPublication.authors.like('%{0}%'.format(name))).all()
    #






    # for r, d, f in os.walk("/Users/jj/private/geopd/data/projects/6/papers/"):
    #     for name in f:
    #         spname = name.split("_")
    #         print spname
    #         if len(spname) >2:
    #             cp = ContentPublication.query.filter(ContentPublication.authors.like('%{0}%'.format(spname[1]))).all()
    #             if cp and len(cp) == 1 :
    #                 print cp[0].title
    #
    #
    #
    #

            # print os.path.join(r, name)




if __name__ == '__main__':
    main()

