import win32com.client
import psutil
import sys

# Codes for RAS output types
WSEL = 2
MIN_CH_EL = 5
STA_WS_LFT = 36
STA_WS_RGT = 37

# Stations for below codes should probably be pulled from geometry, not from the RAS controller
RIGHT_STA = 264  # right station of a XS
LEFT_STA = 263  # left station of a XS


class LockedPlan(Exception):
    pass


class Profile(object):
    def __init__(self, name, code, rc):
        self.name = name  # Profile name, string
        self.code = code  # Profile code, int - these start at 1, not 0
        self.rc = rc   # RasController object

    def __repr__(self):
        return 'Profile name = "'+self.name + '", Profile code = "' + str(self.code)+'"'


class River(object):
    def __init__(self, name, code, rc):
        self.name = name  # River name, string
        self.code = code  # River code, int - these start at 1, not 0
        self.rc = rc   # RasController object
        self.reaches = self._get_reaches()  # list of Reach objects

    # TODO -  the reach code should probably be pulled from the rascontller, although i+1 seems to work
    def _get_reaches(self):
        """
        Gets list of reaches for river represented by self
        :return: list of Reach objects
        """
        reaches = []
        reach_names = self.rc.output_getreaches(self.code)
        for i, name in enumerate(reach_names):
            new_reach = Reach(name, i+1, self)
            reaches.append(new_reach)
        return reaches

    def __repr__(self):
        return 'River name = "'+self.name + '", River code = "' + str(self.code)+'"'


class Reach(object):
    def __init__(self, name, code, river):
        self.name = name  # Reach name, string
        self.code = code  # Reach code, int - these start at 1, not 0
        self.river = river  # parent River object
        self.rc = self.river.rc   # RasController object
        self.nodes = self._get_nodes()  # list of Reach objects

    # TODO -  the reach code should probably be pullled from the rascontller, although i+1 seems to work
    def _get_nodes(self):
        """
        Gets list of reaches for river represented by self
        :return: list of Reach objects
        """
        reach_id = self.code
        river_id = self.river.code
        nodes = []
        node_ids, node_types = self.rc.output_getnodes(river_id, reach_id)
        for i, node_stuff in enumerate(zip(node_ids, node_types)):
            node_id, node_type = node_stuff
            new_node = Node(node_id, node_type, i+1, self)
            nodes.append(new_node)
        return nodes

    def __repr__(self):
        return 'Reach name = "'+self.name + '", Reach code = "' + str(self.code)+'"'


class Node(object):
    def __init__(self, node_id, node_type, code, reach):
        self.node_id = node_id  # Node name, string
        self.node_type = node_type  # node type: '' (XS), 'BR', 'Culv', 'IS', ... etc
        self.code = code  # Node code, int - these start at 1, not 0
        # The line below is how the code should really be gotten
        # self.code = self.rc.com_rc.Geometry_GetNode(self.river.code, self.reach.code, self.node_id)[0]
        self.reach = reach
        self.river = self.reach.river
        self.rc = self.river.rc   # RasController object

    def value(self, profile, value_type):
        # TODO - this should likely check if this is a bridge due to the 0 in output_nodeoutput
        return self.rc.output_nodeoutput(self.river.code, self.reach.code, self.code, profile.code, value_type)

    def __repr__(self):
        if self.node_type == '':
            node_type = 'XS'
        else:
            node_type = self.node_type
        return 'Node name ="' + self.node_id + '", Node type ="' + node_type + '", Node code = "' + str(self.code) + \
                '"'


class RasController(object):
    def __init__(self):
        # See if RAS is open and abort if so
        if True:
            for p in psutil.process_iter():
                try:
                    if p.name() == 'ras.exe':
                        sys.exit('HEC-RAS appears to be open. Please close HEC-RAS. Exiting.')
                except psutil.Error:
                    pass

        # RAS is not open yet, open it
        # self.com_rc = win32com.client.DispatchEx('RAS500.HECRASController')
        self.com_rc = win32com.client.DispatchEx('RAS41.HECRASController')
        self._plan_lock = False  # get_profiles() seems to lock the current plan in place. Not sure why
    
    def close(self):
        """
        closes RAS
        """
        raise NotImplementedError('This functionality is not yet supported.')
        # QuitRAS() is only in RAS 5, this is currently only set for RAS 4
        # TODO - detect RAS version and respond appropriately
        self.com_rc.QuitRAS()

    def get_current_plan(self):
        """
        Returns name of current plan
        :return: string
        """
        pass
    
    def get_plans(self, basedir=None):
        """
        returns list of plan names
        :param basedir: ???? unknown
        :return: list of strings
        """
        _, names, _ = self.com_rc.Plan_Names(None, None, basedir)
        return names

    def run_current_plan(self):
        """
        Run current plan in RAS
        :return: status, messages - ??, ??
        """
        status, _, messages = self.com_rc.Compute_CurrentPlan(None, None)
        return status, messages

    def set_plan(self, plan):
        """
        Sets current plan in RAS
        :param plan: string - name of plan to use
        """
        # Check if get_profiles() has already been run
        if self._plan_lock:
            raise LockedPlan('The plan can not be changed after running get_profiles(). I don\'t know why')
        self.com_rc.Plan_SetCurrent(plan)
        self.com_rc.PlanOutput_SetCurrent(plan)

    def get_profiles(self):
        """
        Returns list of all profiles as Profile objects
        FYI - Output_GetProfiles (used in get_profiles()) appears to somehow prevent the current plan from being
        changed. self._plan_lock is used to keep track of get_profiles being used.
        :return: list of Profile objects
        """
        self._plan_lock = True  # Prevent plan from changing see above
        river_code = 2  # The value of this term appears to do nothing
        _, profile_names = self.com_rc.Output_GetProfiles(river_code, None)
        profiles = []
        for i, name in enumerate(profile_names):
            new_prof = Profile(name, i+1, self)
            profiles.append(new_prof)
        return profiles

    def get_rivers(self):
        """
        Returns list of all rivers as River objects
        :return: list of River objects
        """
        river_names = self._output_getrivers()
        rivers = []
        for i, name in enumerate(river_names):
            new_prof = River(name, i+1, self)
            rivers.append(new_prof)
        return rivers

    #----------------------   
    # is_output_current() does not appear to work!!!!
    #----------------------
    def is_output_current(self, plan, show=False):
        """
        Returns True if output matches plan
        :param plan: string, name of plan to check
        :param show: boolean - whether or not to show the window
        :return: boolean, string (error messages)
        """
        result, plan_name, unknown_bool, message = self.com_rc.PlanOutput_IsCurrent(plan, show, None)
        print (unknown_bool, message)
        return result, message

    def open_project(self, project):
        """
        Opens project in RAS
        :param project: string - full path to RAS project file (*.prj)
        """
        self.com_rc.Project_Open(project)

    def show(self):
        """
        Makes RAS window visible
        """
        self.com_rc.ShowRas()

    # Methods below here are semi-private and are intended to be called from the River, Reach, and Node classes
    def output_getnodes(self, river_id, reach_id):
        """
        Return node names (stationing) and node types
        Node types may belong to the following non inclusive list: '' (cross section), 'BR', 'Culv', 'IS', ...
        :return: nodes_ids, node_types - two lists of strings
        """
        _, _, _, node_ids, node_types = self.com_rc.Geometry_GetNodes(river_id, reach_id, None, None, None)
        return node_ids, node_types

    def output_getreaches(self, river_num):
        """
        Returns reach names in river numbered river_num
        :param river_num: int
        :return: list of reach names
        """
        _, _, reaches = self.com_rc.Output_GetReaches(river_num, None, None)
        return reaches

    def output_nodeoutput(self, river_id, reach_id, node_id, profile, value_type):
        """
        Return RAS node value
        :param river_id: river code for node
        :param reach_id: reach code for node
        :param node_id: code for node
        :param profile: code for desired profile
        :param value_type: RAS value type (see constants at top of this file)
        :return: float (probably)
        """
        # TODO - the 0 in the next line should be a lot smarter
        value = self.com_rc.Output_NodeOutput(river_id, reach_id, node_id, 0, profile, value_type)[0]
        return value

    # TODO - remove once obsolete - change this to work with Plan objects
    def _current_plan_file(self):
        """
        Returns path and file name of current plan file
        :return: string
        """
        return self.com_rc.CurrentPlanFile()

    # TODO - move into get_rivers()
    def _output_getrivers(self):
        """
        Returns list of names of rivers in current project
        :return: list of strings
        """
        _, rivers = self.com_rc.Output_GetRivers(0, None)
        return rivers

    # TODO - remove this, only in for testing
    def _nodes(self, river_id, reach_id):
        """
        Gets list of reaches for river represented by self
        :return: list of Reach objects
        """
        node_ids, node_types = self.output_getnodes(river_id, reach_id)
        return node_ids, node_types


def main():
    rc = RasController()
    rc.open_project('x:/python/rascontroller/rascontrol/models/HG.prj')
    #rc.open_project('x:/python/rascontroller/ras_model/GHC.prj')

    plans = rc.get_plans()
    print '***************Plans', plans
    print 'current plan at start', rc._current_plan_file()
    plan = plans[0]
    print plan
    #rc.set_plan(plan)
    print 'current plan after set_plan()', rc._current_plan_file()
    result, message = rc.is_output_current(plan, show=True)
    print result
    otherterm = rc.get_profiles()
    print otherterm
    print
    """
    the call to rc.get_profiles() seems to be locking the plan in place. But is it? next step is to check if I can get WSELs
    or similar even after the get_profiles() for right profiles after swapping plans. or bail and just stop the damn
    user from changing the profile =P
    """
    plans = rc.get_plans()
    print '***************Plans', plans
    print 'current plan before set_plan()', rc._current_plan_file()
    plan = plans[0]
    print plan
    rc.set_plan(plan)
    print 'current plan after set_plan()', rc._current_plan_file()
    result, message = rc.is_output_current(plan, show=True)
    print result
    profs = rc.get_profiles()
    print profs
    sys.exit()  # ------------------------------------------------------------------------
    
    
    print rc._current_plan_file()
    #rc.show()
    #print rc.run_current_plan()
    print 'done'
    # print rc.run_current_plan()
    river_id = 2
    reach_id = 1
    profile_id = 1
    node_ids, node_types = rc._nodes(river_id, reach_id)
    # print node_ids, node_types
    if not True:
        for x, y in zip(node_ids, node_types):
            # Get numeric node code
            temp = rc.com_rc.Geometry_GetNode(river_id, reach_id, x)
            print temp
            node_id = temp[0]
            # 0 below is for BR up/down, 2 is code for wsel
            wsel1 = rc.com_rc.Output_NodeOutput(river_id, reach_id, node_id, 0, profile_id, 2)[0]
            #wsel2 = rc.com_rc.Output_NodeOutput(river_id, reach_id, node_id, 0, 2, 2)[0]
            print x,'/', y,'/', node_id,'/', wsel1
            #kkprint x,'/', y,'/', node_id,'/', wsel1, wsel2, wsel1-wsel2
            #sys.exit()


    profs = rc.get_profiles()
    print profs

    rivers = rc.get_rivers()
    for riv in rivers:
        for reach in riv.reaches:
            print riv
            print reach
            for node in reach.nodes:
                print node, node.value(profs[0], MIN_CH_EL)
                for prof in profs:
                    print prof.name, node.value(prof, WSEL)

if __name__ == '__main__':
    main()