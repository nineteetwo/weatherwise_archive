document.addEventListener('DOMContentLoaded', () => {
    const countrySelect = document.getElementById('country-select');
    const citySelect = document.getElementById('city-select');
    let countriesData = [];

    /**
     * Tüm ülkeleri API'den çeker ve listeler
     */
    async function fetchCountries() {
        if (!countrySelect) return;

        try {
            const response = await fetch('https://countriesnow.space/api/v0.1/countries');
            const result = await response.json();
            
            if(!result.error) {
                countriesData = result.data;
                countrySelect.innerHTML = '<option value="">Select Country</option>';
                
                // Ülkeleri alfabetik sırala
                countriesData.sort((a, b) => a.country.localeCompare(b.country)).forEach(item => {
                    const option = document.createElement('option');
                    option.value = item.country;
                    option.textContent = item.country;
                    countrySelect.appendChild(option);
                });
            }
        } catch (error) {
            console.error("Location API Error:", error);
            countrySelect.innerHTML = '<option value="">Failed to load API</option>';
        }
    }

    /**
     * Seçilen ülkeye göre şehir listesini günceller
     */
    function updateCities(selectedCountryName) {
        if (!citySelect) return;

        citySelect.innerHTML = '<option value="">Select City</option>';
        
        if (selectedCountryName) {
            const countryInfo = countriesData.find(item => item.country === selectedCountryName);
            
            if (countryInfo && countryInfo.cities.length > 0) {
                citySelect.disabled = false;
                // Şehirleri alfabetik sırala
                countryInfo.cities.sort().forEach(city => {
                    const option = document.createElement('option');
                    option.value = city;
                    option.textContent = city;
                    citySelect.appendChild(option);
                });
            } else {
                citySelect.innerHTML = '<option value="">No cities found</option>';
                citySelect.disabled = true;
            }
        } else {
            citySelect.innerHTML = '<option value="">Select Country First</option>';
            citySelect.disabled = true;
        }
    }

    // Olay Dinleyicisi
    if (countrySelect) {
        countrySelect.addEventListener('change', (e) => updateCities(e.target.value));
    }

    // Başlat
    fetchCountries();
});