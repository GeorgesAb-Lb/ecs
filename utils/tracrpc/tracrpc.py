# -*- coding: utf-8 -*-
"""
a class for interfacing with Trac via jsonrpc 
"""

import os, sys, tempfile, datetime, subprocess, re
from pprint import pprint
import urllib2, urllib

import json_hack
import jsonrpclib
import codecs

jsonrpclib.config.use_jsonclass = True
jsonrpclib.config.classes.add(datetime.datetime)

def get_editor():
    '''
    returns name of editor the user wants, or None if neither EDITOR environment variable is set nor we have a platform default
    (the result should be called via shell=True, because we need the shell to evaluate the path)
    '''
    if os.getenv("EDITOR", None) is None:        
        if sys.platform == "win32":
            editor = "notepad"
        elif sys.platform in ['darwin', 'linux2']:
            editor = "vi"
        else:
            return None
    else:
        editor = os.getenv("EDITOR")
    return editor

def _get_agilo_links(raw=False, testtrac=False):
    ''' get it somewhere else
usage: calls getlinks.sh as ecsdev@ecsdev.ep3.at
getlinks makes a select * from ecs.agilo_link from database ecsdev as user ecsdev, and pipes its output to stdout
result is a list with source|dest links, to be parsed

this is to be called to construct links from agilo to make the "perfect" validation company documents ,-)

    '''
    from fabric.api import run, env, settings, hide
    env.host_string = 'ecsdev@ecsdev.ep3.at'
    with settings(hide('stdout')):
        if testtrac:
            result = run("~/getlinks_ekreqtest.sh")
        else:
            result = run("~/getlinks.sh")
    if raw:
        return result
    else:
        return _parse_agilo_links(result)

def _parse_agilo_links(text):
    ''' '''
    
    ids = []
    lines = text.splitlines()
    ids = [int(id) for line in text.splitlines() for id in line.split('|')]
    links=[]            #list of ticketlinkstuples, (src,dst)
    linkd = {}          #dict of linksources:[targets]
    reverselinkd = {}   #dict of linktargets:[sources]
    for line in lines:
        src,dst = line.split("|")
        src = int(src)
        dst = int(dst)
        links.append((src,dst))
        if not linkd.has_key(src):
            linkd[src] = [dst]
        else:
            linkd[src].append(dst)
        if not reverselinkd.has_key(dst):
            reverselinkd[dst] = [src]
        else:
            reverselinkd[dst].append(src)
    
    return ids,links,linkd,reverselinkd


class HttpBot():
    ''' '''
    
    tracproto = "https"
    trachost = "ecsdev.ep3.at"
    tracpath = "/project/ekreq"
    #tracurl = "https://ecsdev.ep3.at/project/ekreq"
    tracurl = "%s://%s%s" % (tracproto, trachost, tracpath)
    ticketlinkurl = tracurl +"/links"
    
    username='sharing'
    password='uehkdkDijepo833'
    
    opener = None
    cookie_handler = None
    auth_handler = None
    form_token = None
    
    def __init__(self):
        self.auth_handler = urllib2.HTTPBasicAuthHandler()
        self.auth_handler.add_password(realm='ecsdev.ep3.at',
                                  uri=self.tracurl,
                                  user=self.username,
                                  passwd=self.password)
        self.cookie_handler = urllib2.HTTPCookieProcessor()
        self.opener = urllib2.build_opener(self.auth_handler, self.cookie_handler)
        self.opener.addheaders = [('User-agent', 'frankenzilla/1.0')] #Mozilla/5.0
        urllib2.install_opener(self.opener)
        response = self.opener.open(self.tracurl)
        cj = self.cookie_handler.cookiejar
        self.form_token = None
        for c in cj:
            if c.name == 'trac_form_token':
                self.form_token = c.value
    
    def _update_form_token(self):
        cj = self.cookie_handler.cookiejar
        self.form_token = None
        for c in cj:
            if c.name == 'trac_form_token':
                self.form_token = c.value
        
    def create_ticket_link(self, srcid, destid):
        self._ticket_link(srcid, destid, create=True)
    
    def delete_ticket_link(self, srcid, destid):
        self._ticket_link(srcid, destid, create=False)
        
    def _ticket_link(self, srcid, destid, create=True):
        if create:
            cmd = 'create link'
        else:
            cmd = 'delete link'
        data = urllib.urlencode([('url_orig', '%s/ticket/%d?pane=edit' % (self.tracpath, srcid)),
        ('__FORM_TOKEN', self.form_token),
        ('src', srcid),
        ('dest', destid),
        ('autocomplete_parameter', ''),
        ('cmd', cmd)])
        print "sending '%s' request" % (cmd)
        try:
            response = self.opener.open(self.ticketlinkurl, data)
        except urllib2.HTTPError, e: #, Exception
            if e.getcode() == 500:
                print "something wrent wrong and produced a http error 500 while linking ticket %d with %d (src, dst)" % (srcid, destid)
            else:
                print "unexpected error:"
                print  sys.exc_info()[0]
        except:
            print "Unexpected error:", sys.exc_info()[0]
        
        self._update_form_token()
    
    
class Agilolinks():
    
    fetched_once = False
    testtrac=False
    ids = None
    links = None
    linkdict = None
    reverselinkdict = None
    
    def __init__(self, testtrac=False):
        self.testtrac = testtrac
    
    def updatecache(self):
        self.ids, self.links, self.linkdict, self.reverselinkdict = _get_agilo_links(raw=False, testtrac=self.testtrac)
        self.fetched_once = True
        
    def get_ticket_childs(self, tid):
        if not self.fetched_once:
            self.updatecache()
        if self.linkdict.has_key(tid):
            return self.linkdict[tid]
        else:
            return []
        
    def get_ticket_parents(self, tid):
        if not self.fetched_once:
            self.updatecache()
        if self.reverselinkdict.has_key(tid):
            return self.reverselinkdict[tid]
        else:
            return []
    
class TracRpc():
    '''
    makes the communication with Trac
    '''
    jsonrpc = None
    _url = None
    debugmode = False
    link_cache = None
    httpbot = None
    
    def __init__(self, username, password, protocol, hostname, urlpath, debug=False):
        '''
        example: TracRpc('user', 'password', 'https', 'ecsdev.ep3.at', '/project/ecs')
        '''
        C_TRAC_AUTH_JSON = "login/jsonrpc"
        self._url = '%s://%s:%s@%s%s/%s' % (protocol, username, password, hostname,
                                      urlpath, C_TRAC_AUTH_JSON)
        self.jsonrpc = jsonrpclib.Server(self._url)
        self.debugmode = debug
        self.link_cache = Agilolinks(testtrac = debug)
        self.httpbot = HttpBot()
        
    #see http://stackoverflow.com/questions/682504/what-is-a-clean-pythonic-way-to-have-multiple-constructors-in-python
    @classmethod
    def from_dict(cls, config_dict):
        return cls(config_dict['username'], config_dict['password'], config_dict['proto'], config_dict['host'], config_dict['urlpath'])
    
    @staticmethod
    def _safe_rpc(func, *args, **kwargs):
        '''
        wrapper function for any rpc call
        '''
        try:
            result = func(*args, **kwargs)
        except jsonrpclib.ProtocolError as (strerror):
            print "Json RPC ProtocolError: %s" % strerror
            return None
        return result
    
    def multicall(self):
        return jsonrpclib.MultiCall_agilo(self.jsonrpc)

    @staticmethod
    def _ticket2text(ticket):
        '''
        return ticket dict as string with newlines
        '''
        return "%s%s%s%s%s" % (ticket['summary'], os.linesep, os.linesep,
                               ticket['description'], os.linesep)
    
    @staticmethod
    def _text2ticket(text):
        '''
        convert text into a simple ticket dict
        '''
        ticket = {}
        lines = text.splitlines()
        ticket['summary'] = lines[0] if len(lines) > 0 else None
        if len(lines) > 1:
            descr_begin = 1 if lines[1] != "" else 2
            ticket['description'] = os.linesep.join(lines[descr_begin:])
        else:
            ticket['description'] = None
        ticket['remaining_time'] = None
        ticket['type'] = None
        return ticket
    
    @staticmethod
    def _smartertext2ticket(text):
        ''' '''
        
        nl = u'\n'
        ticket={}
        lines = text.splitlines()
        #ticket['summary'] = lines[0] if len(lines) > 0 else None
        #ticket['milestone'] = lines[1].replace('Milestone=', '')
        #ticket['priority'] = lines[2].replace('Priority=', '')
        #ticket['description'] = nl.join(lines[4:len(lines)])
        
        ticket['summary'] = lines[0] if len(lines) > 0 else None
        i=0
        for line in lines:
            if re.search('^Milestone=', line) != None:
                ticket['milestone'] = re.sub('^Milestone=', '', line)
            if re.search('^Priority=', line) != None:
                ticket['priority'] = re.sub('^Priority=', '', line)
            if re.search('^Childlinks=', line) != None:
                tmp = re.sub('^Childlinks=', '', line)
                tmp = tmp.split(',')
                tmpclinks = []
                for link in tmp:
                    if link.strip() != '':
                        tmpclinks.append(int(link.strip()))
                ticket['childlinks'] = tmpclinks
            if re.search('^Parentlinks=', line) != None:
                tmp = re.sub('^Parentlinks=', '', line)
                tmp = tmp.split(',')
                tmpplinks = []
                for link in tmp:
                    if link.strip() != '':
                        tmpplinks.append(int(link.strip()))
                ticket['parentlinks'] = tmpplinks
            if line == '---description---':
                ticket['description'] = nl.join(lines[i+1:len(lines)])
            i+= 1
        return ticket
        
    
    @staticmethod
    def _smarterticket2text(ticket):
        '''
        return ticket dict as string with newlines
        '''
        descr = ticket['description'].replace(u'\r\n', u'\n')
        summary = ticket['summary']
        nl = u'\n'
        return "%s%sMilestone=%s%sChildlinks=%s%sParentlinks=%s%sPriority=%s%s---description---%s%s%s" % (summary, nl, ticket['milestone'], nl, ticket['childlinks'], nl, ticket['parentlinks'], nl, ticket['priority'], nl, nl, descr, nl)
    
    @staticmethod
    def _minimize_ticket(ticket):
        '''
        remove fields with value None from dict
        '''
        newdict = {}
        for key, value in ticket.iteritems():
            if value is not None:
                newdict[key] = value
        return newdict
    
    @staticmethod
    def pad_ticket_w_emptystrings(ticket, fieldnames):
        '''
        returns new dict with fieldnames set to None if they dont exist in ticket
        '''
        new_ticket = {}
        for key,val in ticket.iteritems():
            new_ticket[key] = val if val is not None else ''
        for name in fieldnames:
            new_ticket[name] = ticket[name] if ticket.has_key(name) and ticket[name] is not None else ''
        
        return new_ticket

    def _get_field(self, rawticket, fieldname):
            '''
            return field value or None out of the list returned by rpc call
            '''
            return rawticket[3][fieldname] if rawticket[3].has_key(fieldname) else None
    
    def _get_ticket(self, tid):
        '''
        fetches a ticket and return simple dict w/ ticket contents
        '''
        rawticket = self._safe_rpc(self.jsonrpc.ticket.get, tid)
        if not rawticket:
            return None
        ticket = self._get_ticket_from_rawticket(rawticket)
        return ticket
    
    def _get_ticket_from_rawticket(self, rawticket):
        if not rawticket:
            return None
        else:
            ticket = {}
            ticket['id'] = rawticket[0]
            ticket['summary'] = self._get_field(rawticket, 'summary')
            ticket['description'] = self._get_field(rawticket, 'description')
            ticket['remaining_time'] = self._get_field(rawticket, 'remaining_time')
            ticket['type'] = self._get_field(rawticket, 'type')
            ticket['cc'] = self._get_field(rawticket, 'cc')
            ticket['location'] = self._get_field(rawticket, 'location')
            ticket['absoluteurl'] = self._get_field(rawticket, 'absoluteurl')
            ticket['ecsfeedback_creator'] = self._get_field(rawticket, 'ecsfeedback_creator')
            ticket['milestone'] = self._get_field(rawticket, 'milestone')
            ticket['priority'] = self._get_field(rawticket, 'priority')
            return ticket
        
    
    def _update_ticket(self, tid, ticket, action=None, comment=None):
        '''
        update any field in a ticket
        '''
        if comment is None:
            comment = ""
        if action is None: 
            action = "leave"
        ticket['action'] = action
        ticket = self._minimize_ticket(ticket)
        
        result = self._safe_rpc(self.jsonrpc.ticket.update, tid, comment, ticket)
        # fixme parse update_result for errors,
        # and return False and error text or whatever)
        return True, ""
    
    def _create_ticket(self, summary, ticket, description='', verbose=False):
        #ticket.create(string summary, string description, struct attributes={}
        result = self._safe_rpc(self.jsonrpc.ticket.create, summary, description, ticket)
        if type(result) == int:
            return True, result
        else:
            return False, result
    
    def create_ticket(self, summary=None, description=None, verbose=False):
        if summary is None:
            sys.stdout.write("summary: ")
            summary = raw_input()
        if description is None:
            sys.stdout.write("description: ")
            description = raw_input()
        
        if summary == '':
            print "a ticket must at least have a summary"
            return
        ticket = {'sprint': 'Sysadmin 8',
        'type': 'task'}
        #'milestone': 'Milestone 8'
        #'remaining_time': '20'
        #'priority': 'important'
        
        success, result = self._create_ticket(summary, ticket, description, verbose)
        if success:
            print "created ticket %d" % result
        else:
            print "error creating ticket:"
            print result
        
        
    
    def show_ticket(self, tid, verbose=False):
        '''
        show simple or verbose ticket representation to user
        '''
        ticket = self._get_ticket(tid)
        if not ticket:
            print "could not fetch ticket %d" % tid
        else:
            if verbose:
                print "Ticket:\t%d" % tid
                print "Summary:"
                print "\t%s" % ticket['summary']
                print "Description:"
                for line in ticket['description'].splitlines():
                    print "\t%s" % line
                print "remaining time: %sh" % ticket['remaining_time']
            else:
                print tid, ticket['summary']
    
    def show_actions(self, tid, verbose=False):
        '''
        print a list of valid actions for a ticket
        '''
        actions = self._get_actions(tid)
        print "actions for ticket %d:" % tid
        for action in actions:
            print "\t%s" % action[0] if not verbose else action
        
        
    def _get_actions(self, tid):
        '''
        get valid actions for a ticket
        '''
        actions = self._safe_rpc(self.jsonrpc.ticket.getActions, tid)
        return actions
    
    def _action_is_valid(self, tid, action):
        '''
        checks if a given action is valid for a given ticket
        '''
        actions = self._get_actions(tid)
        actions = [action for line in actions for action in line[:1]]
        
        if action in actions:
            return True
        else:
            return False
    
    def _resolution_is_valid(self, tid, resolution=None):
        '''
        checks if resolution if resolution is contained in ticket actions as an option
        '''
        if resolution is None:
            return False
        actions = self._get_actions(tid)
        for actionline in actions:
            if actionline[0] == "resolve":
                if resolution in actionline[3][0][2]:
                    return True
        
        return False
        
    
    def edit_ticket(self, tid, comment=None):
        '''
        edits a ticket via texteditor, updates the ticket if contents changed
        '''
        
        editor = get_editor()
        if not editor:
            print "error: i do not know which editor to call, please set EDITOR environment variable"
            return

        ticket = self._get_ticket(tid)
        if not ticket:
            print "error: could not fetch ticket %d" % tid
            return

        tempfd, tempname = tempfile.mkstemp()
        utffd = codecs.open(tempname, "w", encoding="utf-8")
        ticket['description'] = ticket['description'].replace('\r\n', '\n')
        ticket['childlinks'] = ', '.join([str(x) for x in self.link_cache.get_ticket_childs(ticket['id'])])
        ticket['parentlinks'] = ', '.join([str(x) for x in self.link_cache.get_ticket_parents(ticket['id'])])
        utffd.write(self._smarterticket2text(ticket))
        utffd.close()

        editproc = subprocess.Popen(" ".join((editor, tempname)), shell=True)
        editproc.wait()
        
        #newticket = self._minimize_ticket(self._smartertext2ticket(codecs.open(tempname, "r", encoding="utf-8").read()))
        
        try:
            newticket = self._minimize_ticket(self._smartertext2ticket(codecs.open(tempname, "r", encoding="utf-8").read()))
            
        except Exception, e:
            print Exception, e
            os.remove(tempname)
            raise Exception
            #abort("exception")
            
        ticket['childlinks'] = [x for x in self.link_cache.get_ticket_childs(ticket['id'])]
        ticket['parentlinks'] = [x for x in self.link_cache.get_ticket_parents(ticket['id'])]
        """print "clinks:"
        pprint(newticket['childlinks'])
        pprint(ticket['childlinks'])
        print "plinks:"
        pprint(newticket['parentlinks'])
        pprint(ticket['parentlinks'])"""
        
        if newticket['childlinks'] != ticket['childlinks']:
            #print "would update ticket links"
            self.link_tickets(ticket['id'], newticket['childlinks'], deletenonlistedtargets=True)
            print "updated ticket child links"
        if newticket['parentlinks'] != ticket['parentlinks']:
            print "parentlinks:"
            print "THIS is not working yet! i have to edit all parent tickets and delete the actual ticket.id from their child links"
            """
            for pid in newticket['parentlinks']:
                self.link_tickets(pid, [ticket['id']], deletenonlistedtargets=False)
            print "updated ticket parent links - experimental"
            
            """
            
        #can't just compare dicts here
        #ticket will have type & remaining_time set in most cases
        if ticket['summary'] != newticket['summary'] or ticket['description'] != newticket['description']\
            or ticket['priority'] != newticket['priority'] or ticket['milestone'] != newticket['milestone']:
            success, additional = self._update_ticket(tid, newticket, comment=comment)
            print "updated ticket via rpc"
            # fixme: check if successfull
        else:
            print "ticket didn't change - not updated(via rpc) - you saved bandwidth"
    
    
    def update_remaining_time(self, tid, new_time, comment=None):
        '''
        udpates the remaining_time field of a ticket if it changed
        '''
        if new_time is None:
            print "error: I won't set remaining_time to 'None'"
            return
        
        ticket = self._get_ticket(tid)
        if not ticket:
            print "could not fetch ticket %d" % tid
            return
        
        old_time = None
        if ticket['remaining_time'] != '':
            old_time = ticket['remaining_time']
            old_time = float(old_time) if '.' in old_time else int(old_time)
            new_time = float(new_time) if '.' in new_time else int(new_time)
        
        if old_time != new_time:
            ticket['remaining_time'] = new_time
            self._update_ticket(tid, ticket, comment=comment)
        else:
            print "remaining time did not change - not updated - bandwidth saved"
            
    
    def close_ticket(self, tid, resolution=None, comment=None):
        '''
        sets a ticket to closed or testing w/ corresponding resolution depending on ticket type
        '''
        ticket = self._get_ticket(tid)
        if not ticket:
            print "could not fetch ticket %d" % tid
            return
        
        #user can override story/bug closing (--> testing/sharing)
        #by setting a resolution
        if resolution is None and (ticket['type'] == 'story' or ticket['type'] == 'bug'):
            action = 'testing'
        elif resolution is not None:
            #only do the extra rpc call(check actions)
            #if user supplies custom resolution
            if not self._resolution_is_valid(tid, resolution):
                print "invalid resolution: %s" % resolution
                return
            ticket['action_resolve_resolve_resolution'] = resolution
            action = 'resolve'
        else:
            ticket['action_resolve_resolve_resolution'] = 'fixed'
            action = 'resolve'
        
        success, additional = self._update_ticket(tid, ticket, action, comment)
        #fixme: check if successfull
    
    
    def accept_ticket(self, tid, comment=None):
        '''
        accept a ticket, if it's valid actions include the accept action
        '''
        if not self._action_is_valid(tid, 'accept'):
            print "You cannot accept ticket %d" % tid
            return
        
        ticket = {}
        action = 'accept'
        success, additional = self._update_ticket(tid, ticket, action, comment)
        #fixme: check if successfull
        
    
    def reopen_ticket(self, tid, comment=None):
        '''
        reopen a ticket, if possible 
        '''
        
        if not self._action_is_valid(tid, 'reopen'):
            print "You cannot reopen ticket %d" % tid
            return
        
        ticket = {}
        action = 'reopen'
        success, additional = self._update_ticket(tid, ticket, action, comment)
        #fixme: check if successfull
        
    def _get_ticket_report(self, username=None, query=None):
        '''
        get a ticket report from trac
        '''
        query_base = "status=accepted&status=assigned&status=new\
&status=reopened&status=testing&group=type&order=priority\
&col=id&col=summary&col=status&col=type&col=priority\
&col=milestone&col=component"
        if query is None:
            if username is not None:
                query = "%s&owner=%s" % (query_base, username)
            else:
                query = query_base
        
        ticket_ids = self._safe_rpc(self.jsonrpc.ticket.query, query)
        tickets = []
        mc = self.multicall()
        for tid in ticket_ids:
            mc.ticket.get(tid)
        results = self._safe_rpc(mc)
        
        if results:
            for result in results.results['result']:
                tickets.append(self._get_ticket_from_rawticket(result['result']))
        
        return tickets
    
    def delete_tickets_by_query(self, query=None, verbose=None, doublecheck=False):
        if query is None:
            return None
        
        ticket_ids = self._safe_rpc(self.jsonrpc.ticket.query, query)
        ticket_types = []
        tickets = []
        mc = self.multicall()
        for tid in ticket_ids:
            mc.ticket.get(tid)
        results = self._safe_rpc(mc)
        for result in results.results['result']:
            tickets.append(self._get_ticket_from_rawticket(result['result']))
        
        allowed_types_2_delete = ['praise', 'problem', 'idea', 'question']
        #allowed_types_2_delete = ['praise', 'problem', 'question']
        for ticket in tickets:
            if ticket['type'] not in allowed_types_2_delete:
                #return False, "bad ticket type in query wont delete anything"
                raise Exception('delete_by_query_error', 'bad ticket type in query wont delete anything')
        
        if not doublecheck:
            print "would delete %d tickets" % len(tickets)
            return True,query
        else:
            mc = self.multicall()
            for tid in ticket_ids:
                mc.ticket.delete(tid)
                pass
            results = self._safe_rpc(mc)
            print "u just did a scary thing" 
        
        
    
    def show_ticket_report(self, username=None, verbose=False, termwidth=80, query=None):
        '''
        show a trac ticket report to the user
        '''
        if query is None:
            print "ticket report for '%s'" % username
        
        tickets = self._get_ticket_report(username=username, query=query)
        if verbose:
            for ticket in tickets:
                print "Ticket:\t%d" % ticket['id']
                print "Summary:"
                print "\t%s" % ticket['summary']
                print "Description:"
                for line in ticket['description'].splitlines():
                    print "\t%s" % line
                print "remaining time: %sh" % ticket['remaining_time'] if ticket['remaining_time'] is not None else '-'
                print ""
            
        else:
            print " ID  SUMMARY%sRT" % (' ' * (termwidth - 16))
            for ticket in tickets:
                truncated_line = ticket['summary'][0:termwidth-10]
                print "%4s %s %s%sh" % (ticket['id'],
                                        ticket['summary'][0:termwidth-10],
                                        ' '*(termwidth-10-len(truncated_line)),
                                        ticket['remaining_time'] if ticket['remaining_time'] is not None else '-')
    
    def simple_query(self, query=None, verbose=False, only_numbers=False):
        ''' '''
        
        if not query:
            print "please supply a query"
            return
        ticket_ids = self._safe_rpc(self.jsonrpc.ticket.query, query) # XXX trac has max=100 many queries
        
        if only_numbers:
            print "ticket IDs:"
            idlist = " ".join(unicode(id) for id in ticket_ids)
            print idlist
            print ""
            print "fetched %s tickets" % len(ticket_ids)
            return
        
        tickets = []
        mc = self.multicall()
        for tid in ticket_ids:
            mc.ticket.get(tid)
        results = self._safe_rpc(mc)
        
        for result in results.results['result']:
            tickets.append(self._get_ticket_from_rawticket(result['result']))
        
        #print " ID  summary                            milestone      priority"
        print "%4s %30s %16s %10s" % ('ID','summary','milestone','priority')
        for t in tickets:
            if len(t['summary']) < 30:
                pass
            if len(t['milestone']) < 10:
                pass
            print "%4s %30s %16s %10s" % (t['id'],t['summary'][:30],t['milestone'],t['priority'])
            #print t['id'],t['summary'][:30],t['milestone'],t['priority']
            
        print ""
        print "fetched %s tickets" % len(tickets)
    
    def batch_edit(self, query=None, verbose=False):
        ''' '''
        if not query:
            print "please supply a query"
            return
        ticket_ids = self._safe_rpc(self.jsonrpc.ticket.query, query)
        
        for id in ticket_ids:
            print "editing ticket %s" % id
            self.edit_ticket(id, comment=None)
            print "press any key to continue or CTRL-C to quit"
            tmpuser = raw_input()
        
                
    def link_tickets(self, srcid=None, destids=None, deletenonlistedtargets=False):
        ''' '''
        import urllib2, urllib
        if not srcid:
            print "no source ticket id specified for linking - returning"
            return
        
        if len(destids) < 1:
            print "no target ticket id(s) specified for linking - returning"
            return
        
        print "linking ticket %d with %s" % (srcid, destids)
        
        targetids = []
        #check that no duplicate link is tried to be created
        srclinks = self.link_cache.get_ticket_childs(srcid)
        if srclinks != None:
            for tid in destids:
                if tid not in srclinks:
                    targetids.append(tid)
                else:
                    print "ticket %d already linked with ticket %d. ignoring it." % (tid, srcid)
                    pass
        else:
            targetids = destids
        
        #delete ticket links not supplied as arg
        if deletenonlistedtargets and srclinks != None:
            for tid in srclinks:
                if tid not in destids:
                    self.httpbot.delete_ticket_link(srcid, tid)
        
        #check if targetIDs exist as tickets:
        #FIXME: here a multicall would be better
        for tid in targetids:
            if self._get_ticket(tid) == None:
                print "ticket %d does not exist.ignoring it" % tid 
                targetids.remove(tid)
        
        #check if src exists:
        if self._get_ticket(srcid) == None:
            print "src ticket %d does not exist. returning!" % srcid
            return
        
        #do the actual linking:
        for tid in targetids:
            self.httpbot.create_ticket_link(srcid, tid)
        if len(targetids) > 0:
            self.link_cache.updatecache()
        
    def linktest(self):
        #pprint(self._safe_rpc(self.jsonrpc.ticket.get, 2921))
        #self._get_ticket_links()
        #self.link_tickets(2921, [1898, 2922])
        #self.link_tickets(2921, [1898], deletenonlistedtargets=True)
        self.link_tickets(2921, [2920], deletenonlistedtargets=False)
        #self.httpbot.delete_ticket_link(2921, 1898)
        #print "trying to link 504 w 2921 & 1337:"
        #self.link_tickets(504, [2921, 1337])
        
                
    def _get_ticket_links(self):
        pprint(_get_agilo_links(testtrac=True))
        



