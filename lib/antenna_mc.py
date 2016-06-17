import math
import numpy
import util
import controller
import random
from antenna import *
from user import *
from util import *

DEBUG = False

def debug_printf(string):
    if DEBUG:
        print(string)


class AntennaMc(Antenna):

    def __init__(self, id, type, pos, radius, grid, bw = 1.4):
        Antenna.__init__(self, id, type, pos, radius, grid, bw)

    def init_mc(self, antennas, nAntennas):
        if len(self._ues) == 0:
            return

        debug_printf("\n##########################\n## STARTING MONTE CARLO ##\n##########################\n")
        self._others_ant = []
        self.list_antennas_in_antennas(antennas, nAntennas)
        self.NPARTICLES = 100
        self.L_BETA       = 0.1
        self.L_LAMBDA     = 0.1
        self.L_UPSILON    = 0.1
        self.E_DEALTA     = 0.2
        self.TOTAL_RBS   = 100
        self._antenna_energy_efficient = 0
        self.mc_data_rate = np.zeros(shape=(self.NPARTICLES))
        self.mc_power_consumption = np.zeros(shape=(self.NPARTICLES))
        self.mc_high_rate_constraint = np.zeros(shape=(self.NPARTICLES))
        self.mc_low_rate_constraint = np.zeros(shape=(self.NPARTICLES))
        self.mc_interference_reuse_constraint = np.zeros(shape=(self.NPARTICLES))
        self.mc_maximum_transmit_power_constraint = np.zeros(shape=(self.NPARTICLES))
        self.mc_antenna_energy_efficient = np.zeros(shape=(self.NPARTICLES))
        #self.mc_cnir = numpy.zeros(shape=(self.NPARTICLES, len(self._ues), self.TOTAL_RBS))
        self.mc_a = numpy.zeros(shape=(self.NPARTICLES,len(self._ues), self.TOTAL_RBS))
        #self.mc_p = numpy.zeros(shape=(self.NPARTICLES,len(self._ues), self.TOTAL_RBS))
        self._cnir = numpy.zeros(shape=(len(self._ues), self.TOTAL_RBS))
        self._a = numpy.zeros(shape=(len(self._ues), self.TOTAL_RBS))
        self._p = numpy.zeros(shape=(len(self._ues), self.TOTAL_RBS))
        #self._w = numpy.zeros(shape=(len(self._ues), self.TOTAL_RBS))
        self.mc_roulette = numpy.zeros(shape=(self.NPARTICLES))


    def clean_mc_variables(self):
        self.mc_data_rate = np.zeros(shape=(self.NPARTICLES))
        self.mc_power_consumption = np.zeros(shape=(self.NPARTICLES))
        self.mc_high_rate_constraint = np.zeros(shape=(self.NPARTICLES))
        self.mc_low_rate_constraint = np.zeros(shape=(self.NPARTICLES))
        self.mc_interference_reuse_constraint = np.zeros(shape=(self.NPARTICLES))
        self.mc_maximum_transmit_power_constraint = np.zeros(shape=(self.NPARTICLES))
        self.mc_antenna_energy_efficient = np.zeros(shape=(self.NPARTICLES))
        #self.mc_cnir = numpy.zeros(shape=(self.NPARTICLES, len(self._ues), self.TOTAL_RBS))
        self.mc_a = numpy.zeros(shape=(self.NPARTICLES,len(self._ues), self.TOTAL_RBS))
        #self.mc_p = numpy.zeros(shape=(self.NPARTICLES,len(self._ues), self.TOTAL_RBS))
        self.mc_roulette = numpy.zeros(shape=(self.NPARTICLES))


    def list_antennas_in_antennas(self, antennas, nAnt):
        for ant in antennas:
            if ant._id != antennas[nAnt]._id:
                antennas[nAnt]._others_ant.append(antennas[nAnt])

            #ant.init_ee(grid.TOTAL_RBS, antennas[nAnt]._others_ant, i)  

    def ee_partial_calc(self,pt,ue,rb):
        self.mc_data_rate[pt] += (self.mc_a[pt,ue,rb] * Antenna.B0 * math.log(1+(self._cnir[ue,rb] * self._p[ue,rb])))
        self.mc_power_consumption[pt] += (self.mc_a[pt,ue,rb] * self._p[ue,rb])
        if self._ues[ue]._type == User.HIGH_RATE_USER:
            self.mc_high_rate_constraint[pt] += self.L_BETA * ((self.mc_a[pt,ue,rb] * Antenna.B0 * math.log(1+(self._cnir[ue,rb] * self._p[ue,rb])) - Antenna.NR))
        else:
            self.mc_low_rate_constraint[pt] += self.L_BETA * ((self.mc_a[pt,ue,rb] * Antenna.B0 * math.log(1+(self._cnir[ue,rb] * self._p[ue,rb])) - Antenna.NER))
        self.mc_interference_reuse_constraint[pt] += self.L_LAMBDA * (self.E_DEALTA - (self.mc_a[pt,ue,rb] * self._p[ue,rb] * Antenna.DR2M * Antenna.PMmax ))
        self.mc_maximum_transmit_power_constraint[pt] += self.mc_a[pt,ue,rb] * self._p[ue,rb]


    def ee_final_calc(self,pt):
        self.mc_power_consumption[pt] = Antenna.EFF * self.mc_power_consumption[pt] + Antenna.PRC + Antenna.PBH
        self.mc_interference_reuse_constraint[pt] = self.E_DEALTA - self.mc_interference_reuse_constraint[pt]
        self.mc_maximum_transmit_power_constraint[pt] = self.L_UPSILON * self.mc_maximum_transmit_power_constraint[pt]
        if self.type == self.BS_ID:
            self.mc_interference_reuse_constraint[pt] = Antenna.PMmax - self.mc_interference_reuse_constraint[pt]
        else:        
            self.mc_interference_reuse_constraint[pt] = Antenna.PRmax - self.mc_interference_reuse_constraint[pt]
        
        debug_printf('DataRate: ' + str(self.mc_data_rate[pt]))
        debug_printf('PowerConsumption: ' + str(self.mc_power_consumption[pt]))
       
        self.mc_antenna_energy_efficient[pt] = self.mc_data_rate[pt] - (self._antenna_energy_efficient * self.mc_power_consumption[pt]) + self.mc_high_rate_constraint[pt] + self.mc_low_rate_constraint[pt] + self.mc_interference_reuse_constraint[pt] + self.mc_maximum_transmit_power_constraint[pt]
        debug_printf('EnergyEfficient: ' + str(self.mc_antenna_energy_efficient[pt]))

    def interference_calc(self, grid):
        for ue in range (0, len(self._ues)):
            for rb in range (0, self.TOTAL_RBS):
                self._cnir[ue][rb] = self.power_interfering(self._ues[ue], rb, grid._antennas)
                self._p[ue][rb] = self.calculate_p(ue, rb)
                #self._w[ue][rb]= self.waterfilling_optimal(ue, rb)

    def power_interfering(self, ue, rb, antennas):
        interference = 0
        Gt = 0.1                       #transmission antenna gain
        Gr = 0.1                       #receiver antenna gain
        Wl = (3/19.0)                  #Comprimento de onda considerando uma frequencia de 1.9 GHz
        for ant in antennas:
            if (ue._connected_antenna._id != ant._id and hasattr(ant, '_a') and sum(ant._a[:,rb])>0):
                index = numpy.argmax(ant._a[:,rb])
                R  =  dist(ue, ant)
                interference += ant._a[index,rb] * ant._p[index,rb] * (Gt * Gr * ( Wl / math.pow((4 * math.pi * R), 2)))
                #print "Interference: ", interference
            #else:
                #interference += path_loss(ue, ant)
                #print "Path loss: ", path_loss(ue, ant)

        return interference


    def calculate_p(self, ue, rb):
        #Obtain P in W                                                                                
        #p = self.waterfilling_optimal(n,k) - (1 / self._cnir[n][k])  
        N = 0.000000000001             #ruido
        Pr = N * (math.pow(2,4.5234)-1)#receivedpower 
        Gt = 0.1                       #transmission antenna gain
        Gr = 0.1                       #receiver antenna gain
        Wl = (3/19.0)                  #Comprimento de onda considerando uma frequencia de 1.9 GHz
        R  = dist(self._ues[ue], self) #distance between antennas 
        Ar =  self._cnir[ue, rb]            #interference plus pathloss
        p = (Pr + Ar) / (Gt * Gr * ( Wl / math.pow((4 * math.pi * R), 2)))                                            
        return p

    def initial_particles(self):
        nUes = len(self._ues)
        for pt in range(0,self.NPARTICLES):
            for rb in range(0,self.TOTAL_RBS): #RB
                #ue = random.randint(-(nUes/3),nUes)-1 #Usuario
                ue = self.random_by_cnir_p(rb, None)
                if ue > 0:
                    self.mc_a[pt,ue,rb] = 1
                    #self.mc_cnir[pt,ue,rb] = self._cnir[ue][rb]
                    #self.mc_p[pt,ue,rb] = self.calculate_p(ue, rb) # aqui tu calcula p
                    self.ee_partial_calc(pt,ue,rb)
            self.ee_final_calc(pt) 
        debug_printf("----- PARTICULA " + str(pt+1) + " -----")
        debug_printf("A = \n" + str(numpy.matrix(self.mc_a[pt])))
        debug_printf("P = \n" + str(numpy.matrix(self._p)))
        debug_printf("CNIR = \n" + str(numpy.matrix(self._cnir)))


    def new_particles_generation(self):
        nUes = len(self._ues)
        for pt in range(0,self.NPARTICLES):
            selected_particle = self.mc_ant_a[self.mc_roulette[pt]]
            for rb in range(0,self.TOTAL_RBS):
                # como gerar a matript a baseada na mSel?????
                #if random.choice([True, False, False]): #30% de chance de trocar
                #    ue = random.randint(-(nUes/3),nUes)-1 #Usuario
                #    if ue > 0:        
                #        self.mc_a[pt,ue,rb] = 1
                #        #self.mc_cnir[pt,ue,rb] =  self._cnir[ue][rb]                        
                #        #self._p[ue,rb] =  self.calculate_p(ue, rb)
                #        self.ee_partial_calc(pt,ue,rb)
                #else:
                #    ue = numpy.argmax(self.mc_ant_a[pt,:,rb])
                #    self.mc_a[pt,ue,rb] = 1
                #    #self.mc_cnir[pt,ue,rb] = self._cnir[ue][rb]
                #    #self._p[pt,ue,rb] = self.calculate_p(ue, rb)                     
                #    self.ee_partial_calc(pt,ue,rb)
                ue = self.random_by_cnir_p(rb, selected_particle)
                if ue > 0:
                    self.mc_a[pt,ue,rb] = 1
                    self.ee_partial_calc(pt,ue,rb)
            self.ee_final_calc(pt) 

            #TODO: atualizar multiplicadores de lagrange
            #self.mt_update_l(pt)

    def random_by_cnir_p(self, rb, particle):
        roleta_ues = numpy.zeros(shape=(len(self._ues))) 
        ant = 0       
        mean = 0
        for ue in range(0, len(self._ues)):
            rsnr = 1
            if (max(self._cnir[:,rb])!=0):
                rsnr = (self._cnir[ue,rb]/max(self._cnir[:,rb]))
            if (rsnr==0):
                rsnr = 1
            roleta_ues[ue] = (self._p[ue,rb]/max(self._p[:,rb]))/rsnr
            if particle != None:
                roleta_ues[ue] = roleta_ues[ue] * (particle[ue,rb]+1)
            mean = mean + roleta_ues[ue]
            roleta_ues[ue] = roleta_ues[ue] + ant
            ant = roleta_ues[ue]

        #print "Sum: " + str(mean)
        mean = mean/len(self._ues)
        tzero = -mean
        #print "Mean: " + str(mean)
        #print "Tzero: " + str(tzero)
        #print "Max: " + str(max(roleta_ues))

        
        rd = random.uniform(tzero, max(roleta_ues))
        #print "Random: " + str(rd)
        if rd > 0:
            for t in range(0, len(self._ues)):
                if rd < roleta_ues[t]:
                    return t
        return -1

    def backup_particles(self):
        self.mc_ant_a = self.mc_a
 

    def select_current_solution(self):
        index = numpy.argmax(self.mc_antenna_energy_efficient)        
        self._antenna_energy_efficient = self.mc_antenna_energy_efficient[index]        
        debug_printf("Max value element : " + str(self._antenna_energy_efficient))
        self._a = self.mc_a[index]
        #self._p = self.mc_p[index]
        #self._cnir = self.mc_cnir[index]
 

    def spinning_roulette(self):
        area = np.zeros(shape=(self.NPARTICLES))
        result = np.zeros(shape=(self.NPARTICLES))
        total = sum(self.mc_antenna_energy_efficient)
        ant = 0;
        for q in range(0, self.NPARTICLES):
            area[q] = ant + self.mc_antenna_energy_efficient[q]
            ant = area[q]

        #TODO: transformar em uma distribuicao gaussian

        for q in range(0, self.NPARTICLES):
            rd = random.uniform(0.0, total)
            for t in range(0, self.NPARTICLES):
                if rd < area[t]:
                    result[q] = t
                    break

        self.mc_roulette = result


    def raises_temperature(self):
        self.L_BETA += 0.1
        self.L_LAMBDA += 0.1
        self.L_UPSILON += 0.1
        self.E_DEALTA += 0.2

    ##########################
    # Calculo do EE
    #########################
    def obtain_data_rate(self):
        for n in range(0, len(self._ues)):
            for k in range (0, self.TOTAL_RBS):
                self.data_rate += self._a[n][k] * Antenna.B0 * math.log(1
                        + (self._cnir[n][k]*self._p[n][k]))
        #print self.data_rate
        #raw_input(" ")

    def obtain_power_consumition(self):
        result = 0
        for n in range(0, len(self._ues)):
            for k in range(0, self.TOTAL_RBS):
                result += (self._a[n][k] * self._p[n][k])           
        self.total_power_consumition = (self.EFF * result) + self.PRC + self.PBH
                                
    def obtain_energy_efficient(self):
        self.obtain_data_rate()
        self.obtain_power_consumition()
        self.energy_efficient = self.data_rate/self.total_power_consumition
        #print numpy.matrix(self.energy_efficient)
