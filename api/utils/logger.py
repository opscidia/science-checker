import logging, os
from logging.handlers import RotatingFileHandler
from datetime import datetime
from flask import jsonify, request
from flask_restful import Resource

MAX_BYTES=800000000
BACKUP_COUNT=10

class ScitaLogger(object):
    
    def __init__(self, root=None, logdir= None, filename='serverlog.txt', use_log=False):
        
        
        self.root = root
        self.logdir = logdir
        self.use_log = use_log
        
        if use_log:
            
            logging.getLogger("requests").setLevel(logging.CRITICAL)
            logging.getLogger("elasticsearch").setLevel(logging.CRITICAL)
            logging.getLogger("requests_aws4auth").setLevel(logging.CRITICAL)
            logging.getLogger("gensim").setLevel(logging.CRITICAL)
            logging.getLogger("transformers").setLevel(logging.CRITICAL)
            logging.getLogger("boto3").setLevel(logging.CRITICAL)
            logging.getLogger("boto").setLevel(logging.CRITICAL)
            logging.getLogger("elasticsearch_dsl").setLevel(logging.CRITICAL)
            logging.getLogger("urllib").setLevel(logging.CRITICAL)
            logging.getLogger("flask_restful").setLevel(logging.CRITICAL)
            logging.getLogger("traceback").setLevel(logging.CRITICAL)
            logging.getLogger("requests").setLevel(logging.CRITICAL)
            logging.getLogger("util.es_utils").setLevel(logging.CRITICAL)
        
        
        self.logger = logging.getLogger('logger')
        self.logger.setLevel(logging.DEBUG)
        logging.basicConfig(format='%(message)s', level=logging.DEBUG)
        log_format = logging.Formatter('[%(levelname)s] %(asctime)s - %(message)s')
        
        self.create_logdir()
        self.create_log(filename)
        
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(log_format)
        stream_handler.setLevel(logging.INFO)
        self.logger.addHandler(stream_handler)

        info_handler = RotatingFileHandler(self.filename, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT)
        info_handler.setFormatter(log_format)
        info_handler.setLevel(logging.INFO)
        self.logger.addHandler(info_handler)
        
            
        
        
    def init(self, mode):
        starter = datetime.now().strftime('%Y-%m-%d %H-%M-%S')
        self.info(f'System startup createsystem in {mode} mode {starter}', 'Main')
        
    def set_filename(self, filename=None):
        self.filename = filename


    #def get_logger(self):
        #"""Return a logger instance that writes in filename
        #Args:
            #filename: (string) path to log.txt
        #Returns:
            #logger: (instance of logger)
        #"""
       
        #handler = logging.StreamHandler()
        #handler.setLevel(logging.DEBUG)
        #handler.setFormatter(logging.Formatter(
                #'%(asctime)s:%(levelname)s: %(message)s'))
        #logging.getLogger().addHandler(handler)

        #return self.logger
    
    #def get_flogger(self):
        #handler = logging.FileHandler(self.filename)
        #handler.setLevel(logging.DEBUG)
        #handler.setFormatter(logging.Formatter(
                #'%(asctime)s:%(levelname)s: %(message)s'))
        #logging.getLogger().addHandler(handler)

        #return self.logger
    
    #def getLogger(self):
        #if self.filename is not None:
            #return self.get_flogger()
        #else:
            #return self.streamHandler
        

    
    def info(self, text=None, module=None):
        self.logger.info(f'{module}: {text}')
        
    def error(self, text=None, module=None):
        self.logger.error(f'{module}: {text}')
        
        
    def warning(self, text=None, module=None):
        self.logger.warning(f'{module}: {text}')
        
    def debug(self, text=None, module=None):
        self.logger.debug(f'{module}: {text}')
        
        
        


    def create_logdir(self):

        if self.use_log:
            try:
                self.logdir = os.path.join(self.root, self.logdir)
                os.makedirs(self.logdir, exist_ok=True)
            except OSError as e:
                self.logdir = None
                print('[Error:] Impossible to create the logs folder: {}'.format(self.logdir))
        else:
            print('[WARNING:] Logs displaying in console.')
            self.logdir = None
    
    
    
    def create_log(self, filename=None):
        if self.use_log and self.logdir is not None:
            try:
                filename = os.path.join(self.logdir, filename)
                if not os.path.isfile(filename):
                    with open(filename, 'w'): pass
                    print(f'[INFO:] Log {filename} is created.')
                else:
                    print(f'[WARNING:] Log {filename} already exists.')
                
                self.set_filename(filename)
            except Exception as e:
                self.set_filename(None)
                print(f'[WARNING:] Log file {filename} could not be created: {e}')
                
        else:
            print(f'[WARNING:] Log file {filename} could not be created. Maybe because LOG in conf file is {self.use_log} and logdir is {self.logdir}.')
    
    
    
    
    
class Startup(Resource):
    
    def __init__(self, logger=None):
        self.logger = logger
        
        
        
    def get(self):
        
        data = request.args['data']
        
        self.logger.info(f"New session started {datetime.now().strftime('%Y-%m-%d %H-%M-%S')} with {data} app.", 'Startup')
            
        response = jsonify({"message": "session init"})
        response.status_code = 200
        
        return response
        
