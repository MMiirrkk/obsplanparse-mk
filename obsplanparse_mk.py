from lark import Lark, Tree #, logger
from typing import Any, List
import logging

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__.rsplit('.')[-1])

class ObsPlanParse:
    
    def _build_kwargs(self, tree: Tree[Any]):
        
        kwargs_dict = {}

        for child in tree.children:    
            if child.data == 'kwarg':
                for child_2 in child.children:
                    if child_2.data == 'kw':
                        kw = str(child_2.children[0])           
                    if child_2.data == 'val':
                        val = str(child_2.children[0]) 
                        
                kwargs_dict[kw] = val
         
        return kwargs_dict
    
    
    def _build_args(self, tree: Tree[Any]):
        
        all_args_list = []  
        for child in tree.children:
            all_args_list.append(str(child.children[0]))
            
        return all_args_list
    
    
    def _build_command_name(self, tree: Tree[Any]) -> str:
    
        for child in tree.children:
            if child.data == 'word':
                word = str(child.children[0])
    
        return word
    
    
    def _build_command(self, tree: Tree[Any]):
        
        command_dict = {}
        for child in tree.children:
            
            if child.data == 'command_name':
                command_dict['command_name'] = self._build_command_name(child)
          
            if child.data == 'args':
                #todo change this!
                if str(child).find('val')>0:
                    command_dict['args'] = self._build_args(child)
         
            if child.data == 'kwargs':
                #todo change this!
                if str(child).find('val')>0:
                    command_dict['kwargs'] = self._build_kwargs(child)
                              
        return command_dict
    
    
    def _build_all_commands(self, tree: Tree[Any]):
        
        all_commands_list = []
        
        for child in tree.children:
            
            if child.data == 'command':
                  
                if str(child.children[0].data) == 'command_name':
                    all_commands_list.append(self._build_command(child))
                         
                if str(child.children[0].data) == 'sequence':
                    all_commands_list.append(self._build_sequence(child.children[0]))
    
        return all_commands_list
    
    
    def _build_sequence(self, tree: Tree[Any]):
        
        sequence_dict = {}
        for child in tree.children:       
            
            if child.data == 'begin_sequence':
                sequence_dict['begin_sequence'] = 'begin'
                
            if child.data == 'args':
                #todo change this!
                if str(child).find('val')>0:
                    sequence_dict['args'] = self._build_args(child)
         
            if child.data == 'kwargs':
                #todo change this!
                if str(child).find('val')>0:
                    sequence_dict['kwargs'] = self._build_kwargs(child)
            
            if child.data == 'all_commands':
                sequence_dict['all_commands'] = self._build_all_commands(child)
                    
        return sequence_dict
    
    
    def _build_sequences(self, tree: Tree[Any]):
    
        sequence_list = []
        
        for child in tree.children:     
            if child.data == 'sequence':
                sequence_list.append(self._build_sequence(child))
                
        return sequence_list
       
        
    def _parse_text(self, text: str) -> Tree[Any]:

        line_parser = Lark(self.line_grammar)

        parse = line_parser.parse
        
        return parse(self.add_beg_end(text))

    def add_beg_end(self, text):

        txt_to_parse = f"BEGINSEQUENCE \n{text} \nENDSEQUENCE"
        log.debug(txt_to_parse)
        return txt_to_parse

    def _convert_parsed_text(self, parsed_text: Tree[Any]) -> List[Any]:
        return self._build_sequences(parsed_text)
    
    
    def _read_file(self, file_name: str) -> str:

        return str(open(file_name, "r").read())
        
    
    def _write_to_file(self, file_name: str, builded_sequences) ->None:
        
        file = open(file_name, "w")
        log.debug(f'{builded_sequences}')
        #log.debug(f'{builded_sequences[0]["all_commands"][0]["args"]}')
        file.write(str(builded_sequences))
        file.close()

    def make_conversion(self, input_file_name: str, output_file_name: str) -> None:
        
        text = self._read_file(input_file_name)
        par_txt = self._parse_text(text)
        builded_sequences = self._convert_parsed_text(par_txt)
        self._write_to_file(output_file_name, builded_sequences)

    @property
    def line_grammar(self):
        lin_gr =r"""
        ?start: sequences
        !sequences      : sequence*
        !sequence       : end_line* begin_sequence args kwargs comment? separator all_commands end_sequence comment? (end_line* comment?)*
        !all_commands   : (command separator)*
        !command        : (command_name args kwargs | sequence) comment?
        !command_name   : word
        kwargs          : kwarg*
        args            : val*
        kwarg           : kw "=" (val ",")+ val | kw "=" val
        !begin_sequence : "BEGINSEQUENCE"
        !end_sequence   : "ENDSEQUENCE"
        separator       : end_line+
        word            : /[^{BEGINSEQUENCE}{ }][A-Z]+/
        comment         : /#.*/
        end_line        : /\n/
        !kw             : string_simple
        !val            : string_simple | string_quoted
        ?string_quoted  : /[\"].*[\"]|[\'].*[\']/
        ?string_simple  : /[^\s=\'\"]+/
        %ignore /[ \f]+/
        """
        return lin_gr


if __name__ == '__main__':
    
    opp = ObsPlanParse()
    opp.make_conversion("txt_files/observe_command.txt", "txt_files/observe_command_NEW1.txt")

        
