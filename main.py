import rascontrol

rc = rascontrol.RasController(version='506')
rc.open_project("C:\BhimaRiver\BhimaRiverComp.prj")

rc.run_current_plan()
profile = rc.get_profiles()[0]
print(profile)
cross_sections = [6150]  # Get results for cross sections 100, 200, & 300
wsels = [rc.get_xs(xs).value(profile, rascontrol.WSEL) for xs in cross_sections]
print(rc._simple_node_list('xs'))
print(rc._simple_node_list('xs'))
print(wsels)