#! /usr/bin/env python3
import argparse
import json
import logging
import logging.config
import os, sys, inspect, time
from websocket import create_connection
import socket
from concurrent import futures
from datetime import datetime

import configparser
#import QDAG_helper
#current_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
#parent_dir = os.path.dirname(current_dir)
#sys.path.insert(0, parent_dir)



# Add Generated folder to module path.
PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(PARENT_DIR, 'generated'))
sys.path.append(os.path.join(PARENT_DIR, 'helper_functions'))
import ServerSideExtension_pb2 as SSE
import grpc
from google.protobuf.json_format import MessageToDict
from ssedata import FunctionType
#from scripteval import ScriptEval
import requests
import pysize
import qlist

_ONE_DAY_IN_SECONDS = 60 * 60 * 24
config = configparser.ConfigParser()
#print(url)

class ExtensionService(SSE.ConnectorServicer):
    """
    A simple SSE-plugin created for the HelloWorld example.
    """

    def __init__(self, funcdef_file):
        """
        Class initializer.
        :param funcdef_file: a function definition JSON file
        """
        self._function_definitions = funcdef_file
        #self.ScriptEval = ScriptEval()
        os.makedirs('logs', exist_ok=True)
        log_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logger.config')
        logging.config.fileConfig(log_file)
        logging.info('Logging enabled')
        function_name = "none"

    @property
    def function_definitions(self):
        """
        :return: json file with function definitions
        """
        return self._function_definitions

    @property
    def functions(self):
        """
        :return: Mapping of function id and implementation
        """
        return {
            0: '_rest_single',
            1: '_rest_30',
            2: '_ws_single',
            3: '_ws_batch'
        }

    @staticmethod
    def _get_function_id(context):
        """
        Retrieve function id from header.
        :param context: context
        :return: function id
        """
        metadata = dict(context.invocation_metadata())
        header = SSE.FunctionRequestHeader()
        header.ParseFromString(metadata['qlik-functionrequestheader-bin'])

        return header.functionId


    @staticmethod
    def _rest_single(request, context):
        """
        Rest using single variable
        """
        logging.info('Entering {} TimeStamp: {}' .format(function_name, datetime.now().strftime("%H:%M:%S.%f")))
        url = config.get(function_name, 'url')
        response_rows = []
        
        for request_rows in request:
            # Iterate over rows
            for row in request_rows.rows:
                # Retrieve string value of parameter and append to the params variable
                # Length of param is 1 since one column is received, the [0] collects the first value in the list
                param = [d.strData for d in row.duals][0]
                # Join with current timedate stamp

                payload = '{"data":"' + param + '"}'
                #logging.info('Showing Payload: {}'.format(payload))
                resp = requests.post(url, data=payload)
                #logging.info('Show Breast Cancer Payload Response: {}'.format(resp))
                #logging.info('Show Breast Cancer Payload Response: {}'.format(resp.text))
                result = resp.text
                result = result.replace('"', '')
                #logging.info('Show Breast Cancer Result: {}'.format(result))
                #Create an iterable of dual with the result
                duals = iter([SSE.Dual(strData=result)])
                response_rows.append(SSE.Row(duals=duals))
                # Yield the row data as bundled rows
        yield SSE.BundledRows(rows=response_rows)
        logging.info('Exiting {} TimeStamp: {}' .format(function_name, datetime.now().strftime("%H:%M:%S.%f")))

    @staticmethod
    def _ws_single(request, context):
        """
        Mirrors the input and sends back the same data.
        :param request: iterable sequence of bundled rows
        :return: the same iterable sequence as received
        """
        logging.info('Entering {} TimeStamp: {}' .format(function_name, datetime.now().strftime("%H:%M:%S.%f")))
    
       

        host = socket.gethostname()
        ip_addr = socket.gethostbyname(host)
        # param = "17.99,10.38,122.8,1001,0.1184,0.2776,0.3001,0.1471,0.2419,0.07871,1.095,0.9053,8.589,153.4,0.006399,0.04904,0.05373,0.01587,0.03003,0.006193,25.38,17.33,184.6,2019,0.1622,0.6656,0.7119,0.2654,0.4601,0.1189"
        ws_url = config.get(function_name, 'ws_url')
        token = config.get(function_name, 'token')
        user_name= config.get(function_name, 'username')
        ws_url = ws_url + host +'_'+ ip_addr+'_'+ user_name+'_'
        print(ws_url)
        ws = create_connection(ws_url)
        response_rows = []
        for request_rows in request:
            # Iterate over rows
            
            for row in request_rows.rows:
                # Retrieve string value of parameter and append to the params variable
                # Length of param is 1 since one column is received, the [0] collects the first value in the list
                param = [d.strData for d in row.duals][0]
                # Join with current timedate stamp
                payload = '{"action": "getPrediction" ,"data":"' + param + '"}'
                #logging.info('Showing Payload: {}'.format(payload))
                ws.send(payload)
                #logging.info('Show Breast Cancer Payload Response: {}'.format(resp.text))
                resp =  json.loads(ws.recv())
                result = resp['prediction']
                score = resp['score']
                #print(result)
                #result = result.replace('"', '')
                #logging.info('Show Breast Cancer Result: {},  Score: {}'.format(result, score))
                # Create an iterable of dual with the result
                duals = iter([SSE.Dual(strData=result)])
                response_rows.append(SSE.Row(duals=duals))
                # Yield the row data as bundled rows
        yield SSE.BundledRows(rows=response_rows)
        ws.close()
        logging.info('Exiting {} TimeStamp: {}' .format(function_name, datetime.now().strftime("%H:%M:%S.%f")))

    @staticmethod
    def _ws_batch(request, context):
        """
        Mirrors the input and sends back the same data.
        :param request: iterable sequence of bundled rows
        :return: the same iterable sequence as received
        """
        logging.info('Entering {} TimeStamp: {}' .format(function_name, datetime.now().strftime("%H:%M:%S.%f")))
    
         # Disable caching.
        md = (('qlik-cache', 'no-store'),)
        context.send_initial_metadata(md)


        host = socket.gethostname()
        ip_addr = socket.gethostbyname(host)
        # param = "17.99,10.38,122.8,1001,0.1184,0.2776,0.3001,0.1471,0.2419,0.07871,1.095,0.9053,8.589,153.4,0.006399,0.04904,0.05373,0.01587,0.03003,0.006193,25.38,17.33,184.6,2019,0.1622,0.6656,0.7119,0.2654,0.4601,0.1189"
        ws_url = config.get(function_name, 'ws_url')
        token = config.get(function_name, 'token')
        user_name= config.get(function_name, 'username')
        batch_size = int(config.get(function_name, 'batch_size'))
        print(batch_size)
        print(type(batch_size))
        ws_url = ws_url + host +'_'+ ip_addr+'_'+ user_name+'_'
        print(ws_url)
        ws = create_connection(ws_url)
        response_rows = []
        outer_counter = 1
        inner_counter = 1
        request_counter = 1
        for request_rows in request:
            logging.info('Printing Request Rows - Request Counter {}' .format(request_counter))
            request_counter+=1
            temp = MessageToDict(request_rows) 
            test_rows = temp['rows']
            request_size = len(test_rows)
            logging.info('Bundled Row Number of  Rows - {}' .format(request_size))
            batches = list(qlist.divide_chunks(test_rows, batch_size)) 
            for i in batches:
                payload_t ={"action": "test"}
                payload_t["data"] = i
                print('Size of payload {}' .format(pysize.get_size(payload_t)))
                logging.info('batch number {}'.format(outer_counter))
                ws.send(json.dumps(payload_t))
                print('message sent WS')
                outer_counter +=1
                payload_t.clear()
                for j in i:
                #print(get_size(rows))
                #print(rows)
                #print(type(rows))
                #logging.info('Inner Counter: {}' .format(inner_counter))
                #print(ws.recv())
                    resp =  json.loads(ws.recv())
                    #print(type(resp))
                    #logging.info('Counter: {} Payload Size: {} Breast Cancer Payload Response: {}'.format(inner_counter, get_size(resp), resp))
                    inner_counter +=1
                    result = resp['prediction']
                    score = resp['score']
                    duals = iter([SSE.Dual(strData=result)])
                    #Yield the row data as bundled rows
                    response_rows.append(SSE.Row(duals=duals))
        yield SSE.BundledRows(rows=response_rows)
        ws.close()
        logging.info('Exiting {} TimeStamp: {}'  .format(function_name, datetime.now().strftime("%H:%M:%S.%f")))

    
    @staticmethod
    def _rest_30(request, context):
        """
        Aggregates the parameters to a single comma separated string.

        """
        
        logging.info('Entering {} TimeStamp: {}' .format(function_name, datetime.now().strftime("%H:%M:%S.%f")))
        url = config.get(function_name, 'url')
        # Iterate over bundled rows
        response_rows = []
        for request_rows in request:
            # Iterate over rows
            for row in request_rows.rows:
                # Retrieve string value of parameter and append to the params variable
                # Length of param is 1 since one column is received, the [0] collects the first value in the list
                param = [d.strData for d in row.duals]
                #logging.info('Showing Payload: {}'.format(param))
                # Aggregate parameters to a single string
                #payload =','.join(param)
                payload = '{"data":"' + (','.join(param)) + '"}'
                #logging.info('Showing Payload: {}'.format(payload))
                #result = payload
               
                resp = requests.post(url, data=payload)
                #logging.info('Show Breast Cancer Payload Response: {}'.format(resp.text))
                result = resp.text
                result = result.replace('"', '')
                #logging.info('Show Breast Cancer Result: {}'.format(result))
                # Create an iterable of dual with the result
                duals = iter([SSE.Dual(strData=result)])
                response_rows.append(SSE.Row(duals=duals))
        # Yield the row data as bundled rows
        yield SSE.BundledRows(rows=response_rows)
        logging.info('Exiting Predict Breast Cancer v2 TimeStamp: {}' .format(datetime.now().strftime("%H:%M:%S.%f")))
   
    @staticmethod
    def _cache(request, context):
        """
        Cache enabled. Add the datetime stamp to the end of each string value.
        :param request: iterable sequence of bundled rows
        :param context: not used.
        :return: string
        """
        # Iterate over bundled rows
        for request_rows in request:
            # Iterate over rows
            for row in request_rows.rows:
                # Retrieve string value of parameter and append to the params variable
                # Length of param is 1 since one column is received, the [0] collects the first value in the list
                param = [d.strData for d in row.duals][0]

                # Join with current timedate stamp
                result = param + ' ' + datetime.now().isoformat()
                # Create an iterable of dual with the result
                duals = iter([SSE.Dual(strData=result)])

                # Yield the row data as bundled rows
                yield SSE.BundledRows(rows=[SSE.Row(duals=duals)])

    @staticmethod
    def _no_cache(request, context):
        """
        Cache disabled. Add the datetime stamp to the end of each string value.
        :param request:
        :param context: used for disabling the cache in the header.
        :return: string
        """
        # Disable caching.
        md = (('qlik-cache', 'no-store'),)
        context.send_initial_metadata(md)

        # Iterate over bundled rows
        for request_rows in request:
            # Iterate over rows
            for row in request_rows.rows:
                # Retrieve string value of parameter and append to the params variable
                # Length of param is 1 since one column is received, the [0] collects the first value in the list
                param = [d.strData for d in row.duals][0]

                # Join with current timedate stamp
                result = param + ' ' + datetime.now().isoformat()
                # Create an iterable of dual with the result
                duals = iter([SSE.Dual(strData=result)])
       
                # Yield the row data as bundled rows
                yield SSE.BundledRows(rows=[SSE.Row(duals=duals)])

  

    def GetCapabilities(self, request, context):
        """
        Get capabilities.
        Note that either request or context is used in the implementation of this method, but still added as
        parameters. The reason is that gRPC always sends both when making a function call and therefore we must include
        them to avoid error messages regarding too many parameters provided from the client.
        :param request: the request, not used in this method.
        :param context: the context, not used in this method.
        :return: the capabilities.
        """
        logging.info('GetCapabilities')
        # Create an instance of the Capabilities grpc message
        # Enable(or disable) script evaluation
        # Set values for pluginIdentifier and pluginVersion
        capabilities = SSE.Capabilities(allowScript=True,
                                        pluginIdentifier='Hello World - Qlik',
                                        pluginVersion='v1.1.0')

        # If user defined functions supported, add the definitions to the message
        with open(self.function_definitions) as json_file:
            # Iterate over each function definition and add data to the capabilities grpc message
            for definition in json.load(json_file)['Functions']:
                function = capabilities.functions.add()
                function.name = definition['Name']
                function.functionId = definition['Id']
                function.functionType = definition['Type']
                function.returnType = definition['ReturnType']

                # Retrieve name and type of each parameter
                for param_name, param_type in sorted(definition['Params'].items()):
                    function.params.add(name=param_name, dataType=param_type)

                logging.info('Adding to capabilities: {}({})'.format(function.name,
                                                                     [p.name for p in function.params]))

        return capabilities

    def ExecuteFunction(self, request_iterator, context):
        """
        Execute function call.
        :param request_iterator: an iterable sequence of Row.
        :param context: the context.
        :return: an iterable sequence of Row.
        """
        # Retrieve function id
        func_id = self._get_function_id(context)
        # Call corresponding function
        logging.info('ExecuteFunction (functionId: {})'.format(func_id))
        global function_name 
        function_name = self.functions[func_id]

        return getattr(self, self.functions[func_id])(request_iterator, context)



    def Serve(self, port, pem_dir):
        """
        Sets up the gRPC Server with insecure connection on port
        :param port: port to listen on.
        :param pem_dir: Directory including certificates
        :return: None
        """
        # Create gRPC server
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        SSE.add_ConnectorServicer_to_server(self, server)

        if pem_dir:
            # Secure connection
            with open(os.path.join(pem_dir, 'sse_server_key.pem'), 'rb') as f:
                private_key = f.read()
            with open(os.path.join(pem_dir, 'sse_server_cert.pem'), 'rb') as f:
                cert_chain = f.read()
            with open(os.path.join(pem_dir, 'root_cert.pem'), 'rb') as f:
                root_cert = f.read()
            credentials = grpc.ssl_server_credentials([(private_key, cert_chain)], root_cert, True)
            server.add_secure_port('[::]:{}'.format(port), credentials)
            logging.info('*** Running server in secure mode on port: {} ***'.format(port))
        else:
            # Insecure connection
            server.add_insecure_port('[::]:{}'.format(port))
            logging.info('*** Running server in insecure mode on port: {} ***'.format(port))

        # Start gRPC server
        server.start()
       
        try:
            while True:
                time.sleep(_ONE_DAY_IN_SECONDS)
        except KeyboardInterrupt:
            server.stop(0)
            

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    config.read(os.path.join(os.path.dirname(__file__), 'config', 'qrag.ini'))
    port = config.get('base', 'port')
    parser.add_argument('--port', nargs='?', default=port)
    parser.add_argument('--pem_dir', nargs='?')
    parser.add_argument('--definition_file', nargs='?', default='functions.json')
    args = parser.parse_args()
    # need to locate the file when script is called from outside it's location dir.
    def_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), args.definition_file)
    logging.info('*** Server Configurations Port: {}, Pem_Dir: {}, def_file {} TimeStamp: {} ***'.format(args.port, args.pem_dir, def_file,datetime.now().isoformat()))
    calc = ExtensionService(def_file)
    calc.Serve(args.port, args.pem_dir)