# disco.bot.providers.base


  
  





## Constants

  

  

  

  




## Classes

  ### BaseProvider


_Inherits From _









#### Functions

  #### __init__(self, config)


  
  




  #### exists(self, key)


  
  




  #### keys(self, other)


  
  




  #### get_many(self, keys)


  
  




  #### get(self, key)


  
  




  #### set(self, key, value)


  
  




  #### delete(self, key)


  
  




  #### load(self)


  
  




  #### save(self)


  
  




  #### root(self)


  
  






  ### StorageDict


_Inherits From `UserDict`_









#### Functions

  #### __init__(self, parent_or_provider, key)


  
  




  #### keys(self)


  
  




  #### values(self)


  
  




  #### items(self)


  
  




  #### ensure(self, key, typ)


  
  




  #### update(self, obj)


  
  




  #### data(self)


  
  




  #### key(self)


  
  




  #### __setitem__(self, key, value)


  
  




  #### __getitem__(self, key)


  
  




  #### __delitem__(self, key)


  
  




  #### __contains__(self, key)


  
  









## Functions

  #### join_key(`*args`)


  
  




  #### true_key(key)


  
  




