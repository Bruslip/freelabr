// FreelaBR - Calculator Logic (Frontend)
// Implementa a mesma lógica do backend em JavaScript

class FreelaBRCalculator {
    constructor() {
        // Valores fixos 2025
        this.MEI_DAS_VALUE = 81.90;
        this.MINIMUM_WAGE = 1518.00;
        
        // Informações sobre regimes tributários
        this.taxRegimes = {
            MEI: {
                name: "Microempreendedor Individual (MEI)",
                monthly_cost: this.MEI_DAS_VALUE,
                description: `Valor fixo mensal de R$ ${this.MEI_DAS_VALUE.toFixed(2)} (DAS 2025)`,
                limit: "Faturamento anual até R$ 81.000",
                benefits: ["Simples", "Barato", "Poucas obrigações"],
                drawbacks: ["Limite de faturamento", "Apenas 1 funcionário"]
            },
            PJ_SIMPLES: {
                name: "Simples Nacional - Anexo III",
                percentage: "6% a 33%",
                description: "Alíquota inicial de 6% sobre faturamento",
                limit: "Faturamento anual até R$ 4,8 milhões",
                benefits: ["Menos burocracia", "Alíquota progressiva"],
                drawbacks: ["Aumenta com faturamento", "Obrigações acessórias"]
            },
            PJ_PRESUMIDO: {
                name: "Lucro Presumido",
                percentage: "~16,33%",
                description: "IR + CSLL + PIS/COFINS + ISS",
                limit: "Faturamento anual até R$ 78 milhões",
                benefits: ["Previsível", "Bom para margens altas"],
                drawbacks: ["Mais complexo", "Mais caro que Simples inicial"]
            },
            AUTONOMO: {
                name: "Autônomo (Pessoa Física)",
                percentage: "20% INSS + IR progressivo",
                description: "INSS 20% sobre salário mínimo + IR progressivo",
                limit: "Sem limite",
                benefits: ["Flexível", "Sem burocracia"],
                drawbacks: ["IR progressivo alto", "Menos benefícios"]
            }
        };
    }

    calculate(input) {
        // 1. Calcular horas e dias trabalhados
        const workingDaysPerWeek = input.daysPerWeek;
        const workingWeeksPerYear = 52 - input.vacationWeeks;
        const workingDaysPerYear = workingDaysPerWeek * workingWeeksPerYear;
        const workingDaysPerMonth = workingDaysPerYear / 12;
        
        const workingHoursPerDay = input.hoursPerDay;
        const workingHoursPerMonth = workingHoursPerDay * workingDaysPerMonth;
        
        // 2. Calcular impostos mensais
        const monthlyTaxes = this.calculateMonthlyTaxes(
            input.desiredMonthlyIncome,
            input.taxRegime
        );
        
        // 3. Calcular provisões (férias e 13º)
        let monthlyProvisions = 0;
        if (input.include13th) {
            monthlyProvisions += input.desiredMonthlyIncome / 12;
        }
        if (input.includeVacation) {
            monthlyProvisions += (input.desiredMonthlyIncome / 3) / 12;
        }
        
        // 4. Somar custos totais mensais
        const totalMonthlyCosts = 
            input.desiredMonthlyIncome +  // Pró-labore
            monthlyTaxes +                // Impostos
            monthlyProvisions +           // Provisões
            input.monthlyExpenses +       // Despesas fixas
            input.variableExpenses;       // Despesas variáveis
        
        // 5. Aplicar margem de lucro
        const profitMargin = input.profitMarginPercentage / 100;
        const totalMonthlyRate = totalMonthlyCosts / (1 - profitMargin);
        
        // 6. Calcular valores por unidade de tempo
        const hourlyRate = totalMonthlyRate / workingHoursPerMonth;
        const dailyRate = hourlyRate * workingHoursPerDay;
        const weeklyRate = dailyRate * workingDaysPerWeek;
        
        // 7. Sugerir valores para projetos
        const smallProjectValue = hourlyRate * 30;   // ~30h
        const mediumProjectValue = hourlyRate * 100; // ~100h
        const largeProjectValue = hourlyRate * 200;  // ~200h
        
        // 8. Retornar resultado
        return {
            hourlyRate: hourlyRate,
            dailyRate: dailyRate,
            weeklyRate: weeklyRate,
            monthlyRate: totalMonthlyRate,
            
            totalMonthlyCosts: totalMonthlyCosts,
            totalAnnualCosts: totalMonthlyCosts * 12,
            monthlyTaxes: monthlyTaxes,
            monthlyProvisions: monthlyProvisions,
            netMonthlyIncome: input.desiredMonthlyIncome,
            
            workingHoursPerMonth: Math.round(workingHoursPerMonth),
            workingDaysPerMonth: Math.round(workingDaysPerMonth),
            taxRegime: input.taxRegime,
            
            smallProjectValue: smallProjectValue,
            mediumProjectValue: mediumProjectValue,
            largeProjectValue: largeProjectValue,
        };
    }

    calculateMonthlyTaxes(monthlyIncome, taxRegime) {
        switch (taxRegime) {
            case 'MEI':
                // MEI paga valor fixo mensal
                return this.MEI_DAS_VALUE;
            
            case 'PJ_SIMPLES':
                // Simples Nacional - Anexo III (serviços)
                // Alíquota inicial de 6%
                return monthlyIncome * 0.06;
            
            case 'PJ_PRESUMIDO':
                // Lucro Presumido - alíquota média
                // IR + CSLL + PIS/COFINS + ISS = ~16,33%
                return monthlyIncome * 0.1633;
            
            case 'AUTONOMO':
                // Autônomo - INSS + IR progressivo
                const inss = this.MINIMUM_WAGE * 0.20; // 20% sobre salário mínimo
                const ir = this.calculateProgressiveIR(monthlyIncome);
                return inss + ir;
            
            default:
                return 0;
        }
    }

    calculateProgressiveIR(monthlyIncome) {
        // Tabela IR 2025 (simplificada)
        if (monthlyIncome <= 2259.20) {
            return 0;
        } else if (monthlyIncome <= 2828.65) {
            return (monthlyIncome * 0.075) - 169.44;
        } else if (monthlyIncome <= 3751.05) {
            return (monthlyIncome * 0.15) - 381.44;
        } else if (monthlyIncome <= 4664.68) {
            return (monthlyIncome * 0.225) - 662.77;
        } else {
            return (monthlyIncome * 0.275) - 896.00;
        }
    }

    getTaxInfo(taxRegime) {
        return this.taxRegimes[taxRegime] || {};
    }
}

// Inicializar calculadora
const calculator = new FreelaBRCalculator();

// Elementos do DOM
const form = document.getElementById('calculatorForm');
const resultsSection = document.getElementById('resultsSection');
const profitMarginInput = document.getElementById('profitMargin');
const profitMarginValue = document.getElementById('profitMarginValue');
const taxRegimeSelect = document.getElementById('taxRegime');
const regimeInfo = document.getElementById('regimeInfo');

// Atualizar valor da margem de lucro em tempo real
profitMarginInput.addEventListener('input', (e) => {
    profitMarginValue.textContent = e.target.value;
});

// Atualizar informação do regime tributário
taxRegimeSelect.addEventListener('change', (e) => {
    const info = calculator.getTaxInfo(e.target.value);
    regimeInfo.textContent = info.description || '';
});

// Inicializar info do regime
regimeInfo.textContent = calculator.getTaxInfo('MEI').description;

// Função para formatar moeda
function formatCurrency(value) {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(value);
}

// Handler do formulário
form.addEventListener('submit', (e) => {
    e.preventDefault();
    
    // Coletar inputs
    const input = {
        desiredMonthlyIncome: parseFloat(document.getElementById('monthlyIncome').value),
        hoursPerDay: parseInt(document.getElementById('hoursPerDay').value),
        daysPerWeek: parseInt(document.getElementById('daysPerWeek').value),
        vacationWeeks: 4, // Fixo para MVP
        taxRegime: document.getElementById('taxRegime').value,
        include13th: document.getElementById('include13th').checked,
        includeVacation: document.getElementById('includeVacation').checked,
        monthlyExpenses: parseFloat(document.getElementById('monthlyExpenses').value),
        variableExpenses: parseFloat(document.getElementById('variableExpenses').value),
        profitMarginPercentage: parseFloat(document.getElementById('profitMargin').value)
    };
    
    // Calcular
    const result = calculator.calculate(input);
    
    // Exibir resultados
    displayResults(result, input);
    
    // Mostrar seção de resultados com animação
    resultsSection.classList.remove('hidden');
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
});

// Função para exibir resultados
function displayResults(result, input) {
    // Valores principais
    document.getElementById('hourlyRate').textContent = formatCurrency(result.hourlyRate);
    document.getElementById('dailyRate').textContent = formatCurrency(result.dailyRate);
    document.getElementById('weeklyRate').textContent = formatCurrency(result.weeklyRate);
    document.getElementById('monthlyRate').textContent = formatCurrency(result.monthlyRate);
    
    // Projetos
    document.getElementById('smallProject').textContent = formatCurrency(result.smallProjectValue);
    document.getElementById('mediumProject').textContent = formatCurrency(result.mediumProjectValue);
    document.getElementById('largeProject').textContent = formatCurrency(result.largeProjectValue);
    
    // Detalhamento
    document.getElementById('netIncome').textContent = formatCurrency(result.netMonthlyIncome);
    document.getElementById('monthlyTaxes').textContent = formatCurrency(result.monthlyTaxes);
    document.getElementById('provisions').textContent = formatCurrency(result.monthlyProvisions);
    document.getElementById('totalExpenses').textContent = formatCurrency(input.monthlyExpenses + input.variableExpenses);
    document.getElementById('totalMonthlyCost').textContent = formatCurrency(result.totalMonthlyCosts);
    document.getElementById('workingHours').textContent = result.workingHoursPerMonth + 'h';
}

// Inicializar com cálculo automático ao carregar a página
window.addEventListener('load', () => {
    form.dispatchEvent(new Event('submit'));
});
