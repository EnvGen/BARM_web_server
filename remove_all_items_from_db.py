import app
import argparse

def confirm():
    prompt = 'This will remove ALL ORM tables plus alembic_vesion table from the entire database. Please confirm this action:'

    prompt = '%s [%s]|%s: ' % (prompt, 'y', 'n')

    while True:
        ans = input(prompt)
        if not ans:
            return resp
        if ans not in ['y', 'Y', 'n', 'N']:
            print('please enter y or n.')
            continue
        if ans == 'y' or ans == 'Y':
            return True
        if ans == 'n' or ans == 'N':
            return False

def main(args):
    if not confirm():
        raise Exception("Confirmation was not granted")

    print("Deleting!")

    s =  app.db.session()

    app.db.drop_all()
    s.execute("DROP TABLE alembic_version;")
   # for table in reversed(app.db.metadata.sorted_tables):
   #     print("Deleting {}".format(table))
   #     app.db.metadata.remove(table)
    s.commit()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    args = parser.parse_args()
    main(args)
