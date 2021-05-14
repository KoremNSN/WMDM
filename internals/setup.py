from psiturk.psiturk_config import PsiturkConfig

import subprocess
import configparser
import heroku3
import re
import os

class color:
   PURPLE = '\033[95m'
   CYAN = '\033[96m'
   DARKCYAN = '\033[36m'
   BLUE = '\033[94m'
   GREEN = '\033[92m'
   YELLOW = '\033[93m'
   RED = '\033[91m'
   BOLD = '\033[1m'
   UNDERLINE = '\033[4m'
   END = '\033[0m'

class HerokuSetup():

    def __init__(self):
        # On init, just check to see if git exists
        self.has_git = os.path.isdir('.git')
        self.c = configparser.ConfigParser()
        self.c.read('config.txt')

    # 1. Sets up the git repo to push to heroku
    def initialize_git(self):
        if not self.has_git: 
            subprocess.run(['git', 'init'], stdout=subprocess.PIPE)
            print("Created new git repo in .git/")
        else:
            print("Found existing git repo, using that.")
    
    # 2. Creates a Heroku instance and builds the app
    def initialize_heroku(self):
        api_key = input('Your Heroku API Key: ')
        heroku_conn = heroku3.from_key(api_key.strip())
        app_name = self.c['Heroku Parameters']['app_name'].strip()
        created_new_app = True
        if app_name is not 'NOTYETSET':
            try:
                self.app = heroku_conn.app(app_name)
                created_new_app = False
            except:
                self.app = None
            if not self.app:
                while True:
                    try:
                        self.app = heroku_conn.create_app(name=app_name)
                        break
                    except:
                        app_name = input('Invalid or taken app_name. Please enter a new one (blank for auto-generated): ').strip()
                        if app_name == '':
                            app_name = None
        else: 
            print('App name was not set in config.txt, generating a Heroku app name.')
            self.app = heroku_conn.create_app()
        if created_new_app:
            self.app.install_addon('heroku-postgresql')
            print('Created Heroku app ' + color.BOLD + color.GREEN + self.app.name + color.END + ' with PostgreSQL database.')
        else:
            print('Found existing Heroku app ' + color.BOLD + color.GREEN + self.app.name + color.END + '. Continuing with it.')
            if not any('heroku-postgresql' in addon.plan.name for addon in self.app.addons()):
                self.app.install_addon('heroku-postgresql')
                print('Created a Heroku PostgreSQL database addon in the existing Heroku app.')

    # 3. Uses the Heroku instance to generate the config
    def setup_config_with_heroku(self):
        self.c['Database Parameters']['database_url'] = self.app.config()['DATABASE_URL']
        self.c['Database Parameters']['table_name'] = 'experiment_table'
        self.c['Server Parameters']['host'] = '0.0.0.0'
        self.c['Server Parameters']['threads'] = '1'
        self.c['Shell Parameters']['ad_location'] = 'https://' + self.app.domains()[0].hostname + '/pub'
        self.c['Shell Parameters']['use_psiturk_ad_server'] = 'false'
        self.c['Heroku Parameters']['app_name'] = self.app.name
        with open('config.txt', 'w') as out:
            self.c.write(out)
        print('Configured local ' + color.BOLD + 'config.txt' + color.END + ' to point to remote Heroku domain.')
    
    # 4. Applies local Psiturk settings to Heroku instance
    def setup_heroku_remote_config(self):
        CONFIG = PsiturkConfig()
        CONFIG.load_config()
        new_config = {}
        sections = ['psiTurk Access', 'AWS Access']
        for section in sections:
            for item in CONFIG.items(section):
                new_config[item[0]] = item[1]
        new_config['ON_CLOUD'] = True
        self.app.update_config(new_config)
        print('Built remote Heroku config from AWS and PsiTurk accounts found in local ' + color.BOLD + '.psiturkconfig' + color.END)
    
    # 5. Deploy current Git code to Heroku instance (sets Heroku remote JIC)
    def deploy_code(self):
        result = subprocess.run(['git', 'remote', 'add', 'heroku', 'https://git.heroku.com/' + self.app.name + '.git/' ], capture_output=True)
        if 'fatal' in str(result.stdout):
            subprocess.run(['git', 'remote', 'set-url', 'heroku', 'https://git.heroku.com/' + self.app.name + '.git/' ])
        subprocess.run(['git', 'add', '.'], stdout=subprocess.PIPE)
        subprocess.run(['git', 'commit', '-m', '"Initial commit"'], stdout=subprocess.PIPE)
        subprocess.run(['git', 'push', 'heroku', 'master'], stdout=subprocess.PIPE)

    # START HERE: Timeline for each init task.
    def run(self):
        print(color.BOLD + "\nInitializing Git repo..." + color.END)
        self.initialize_git()

        print(color.BOLD + "\nInitializing Heroku app..." + color.END)
        self.initialize_heroku()

        print(color.BOLD + "\nSetting configurations..." + color.END)
        self.setup_config_with_heroku()
        self.setup_heroku_remote_config()

        print(color.BOLD + "\nLoading initial Git commit..." + color.END)
        self.deploy_code()

        print(color.BOLD + color.GREEN + "\nDONE!" + color.END + " Your Heroku domain: " + color.GREEN + color.BOLD + 
            "https://" + self.app.domains()[0].hostname + color.END + "\nYou may now run " +
            "psiturk locally and create HITs. To push local changes to the remote Heroku instance, simply push commits to heroku/master, " +
            "ie: \n\n\t" + color.YELLOW + 'git add .\n\tgit commit -m "<YOUR MESSAGE>"\n\tgit push heroku master' + color.END + '\n')


if __name__ == "__main__":
    HerokuSetup().run()